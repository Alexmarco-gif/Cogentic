"""Paystack billing service for checkout, verification, and webhooks."""

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.models.organization import Organization
from backend.models.subscription import Subscription
from backend.repositories.pricing_repository import PricingRepository
from backend.services.pricing_service import PricingService


class PaystackError(RuntimeError):
    """Base Paystack integration error."""


class PaystackConfigurationError(PaystackError):
    """Raised when Paystack settings are missing."""


class PaystackVerificationError(PaystackError):
    """Raised when a payment cannot be safely trusted."""


class PaystackService:
    """Billing integration for Paystack subscriptions."""

    PROVIDER = "paystack"
    CURRENCY = "USD"
    BILLING_CYCLE = "monthly"

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.pricing_repo = PricingRepository(db)
        self.pricing_service = PricingService(db)

    @property
    def is_configured(self) -> bool:
        return bool(self.settings.paystack_secret_key)

    def get_public_key(self) -> str | None:
        return self.settings.paystack_public_key

    def verify_webhook_signature(self, body: bytes, signature: str | None) -> bool:
        if not self.settings.paystack_secret_key or not signature:
            return False
        digest = hmac.new(
            self.settings.paystack_secret_key.encode("utf-8"),
            body,
            hashlib.sha512,
        ).hexdigest()
        return hmac.compare_digest(signature, digest)

    async def initialize_subscription_checkout(
        self,
        organization: Organization,
        *,
        user_id: UUID,
        user_email: str,
        target_tier: str,
        callback_url: str | None = None,
    ) -> dict[str, Any]:
        self._ensure_configured()
        amount_subunits = await self._get_tier_amount_subunits(target_tier)
        plan_code = await self.ensure_plan(target_tier, user_id=user_id)
        reference = self._build_reference(organization.id, target_tier)
        payload: dict[str, Any] = {
            "email": organization.billing_email or user_email,
            "amount": amount_subunits,
            "currency": self.CURRENCY,
            "plan": plan_code,
            "reference": reference,
            "metadata": {
                "kind": "tier_upgrade",
                "org_id": str(organization.id),
                "user_id": str(user_id),
                "current_tier": organization.pricing_tier,
                "target_tier": target_tier,
            },
        }
        if callback_url:
            payload["callback_url"] = callback_url

        data = await self._request("POST", "/transaction/initialize", json=payload)
        subscription = await self._get_or_create_subscription(organization.id)
        subscription.provider = self.PROVIDER
        subscription.plan_tier = target_tier
        subscription.billing_cycle = self.BILLING_CYCLE
        subscription.price_cents = amount_subunits
        subscription.currency = self.CURRENCY
        subscription.status = "pending_activation"
        subscription.provider_plan_code = plan_code
        subscription.latest_reference = data.get("reference") or reference
        subscription.provider_metadata = self._merge_metadata(
            subscription.provider_metadata,
            {"checkout_initialize": data},
        )

        settings = dict(organization.settings or {})
        settings["pending_tier_upgrade"] = {
            "status": "checkout_initialized",
            "target_tier": target_tier,
            "current_tier": organization.pricing_tier,
            "requested_by": str(user_id),
            "requested_at": datetime.now(timezone.utc).isoformat(),
            "provider": self.PROVIDER,
            "reference": subscription.latest_reference,
            "plan_code": plan_code,
        }
        organization.settings = settings
        await self.db.flush()

        return {
            "reference": subscription.latest_reference,
            "access_code": data.get("access_code"),
            "authorization_url": data.get("authorization_url"),
            "public_key": self.settings.paystack_public_key,
        }

    async def verify_and_activate_checkout(self, reference: str) -> dict[str, Any]:
        transaction = await self.verify_transaction(reference)
        if transaction.get("status") != "success":
            raise PaystackVerificationError("Payment has not completed successfully")

        metadata = self._coerce_metadata(transaction.get("metadata"))
        org_id_raw = metadata.get("org_id")
        target_tier = metadata.get("target_tier")
        if not org_id_raw or not target_tier:
            raise PaystackVerificationError("Missing billing metadata on transaction")

        organization = await self.db.get(Organization, UUID(str(org_id_raw)))
        if not organization:
            raise PaystackVerificationError("Organization not found for transaction")

        expected_amount = await self._get_tier_amount_subunits(target_tier)
        if int(transaction.get("amount") or 0) < expected_amount:
            raise PaystackVerificationError("Paid amount does not match the tier price")

        customer = transaction.get("customer") or {}
        authorization = transaction.get("authorization") or {}
        plan = transaction.get("plan") or {}
        subscription = await self._get_or_create_subscription(organization.id)
        now = datetime.now(timezone.utc)

        subscription.provider = self.PROVIDER
        subscription.plan_tier = target_tier
        subscription.billing_cycle = self.BILLING_CYCLE
        subscription.price_cents = expected_amount
        subscription.currency = str(transaction.get("currency") or self.CURRENCY)
        subscription.status = "active"
        subscription.provider_customer_code = (
            customer.get("customer_code") or subscription.provider_customer_code
        )
        subscription.provider_plan_code = (
            plan.get("plan_code") or subscription.provider_plan_code
        )
        subscription.latest_reference = reference
        subscription.authorization_code = (
            authorization.get("authorization_code") or subscription.authorization_code
        )
        subscription.current_period_start = subscription.current_period_start or now
        subscription.current_period_end = (
            subscription.current_period_end or now + timedelta(days=30)
        )
        subscription.provider_metadata = self._merge_metadata(
            subscription.provider_metadata,
            {"last_verified_transaction": transaction},
        )

        organization.pricing_tier = target_tier
        organization.billing_cycle_start = now.date()
        organization.credits_allocated_monthly = (
            await self.pricing_service.get_tier_credits(target_tier)
        )
        organization.credits_consumed = 0

        settings = dict(organization.settings or {})
        pending = settings.get("pending_tier_upgrade")
        if isinstance(pending, dict):
            pending.update(
                {
                    "status": "completed",
                    "reference": reference,
                    "completed_at": now.isoformat(),
                    "target_tier": target_tier,
                }
            )
            settings["pending_tier_upgrade"] = pending
        organization.settings = settings
        await self.db.flush()

        return {
            "status": "activated",
            "tier": target_tier,
            "reference": reference,
            "transaction_status": transaction.get("status"),
            "message": f"{target_tier.replace('_', ' ').title()} is now active.",
        }

    async def get_subscription_snapshot(self, org_id: UUID) -> dict[str, Any]:
        subscription = await self._get_subscription_by_org(org_id)
        if not subscription:
            return {
                "provider": None,
                "status": None,
                "plan_tier": None,
                "billing_cycle": None,
                "currency": None,
                "price_cents": None,
                "latest_reference": None,
                "current_period_start": None,
                "current_period_end": None,
                "canceled_at": None,
                "provider_customer_code": None,
                "provider_subscription_code": None,
                "provider_plan_code": None,
                "can_cancel": False,
            }

        return {
            "provider": subscription.provider,
            "status": subscription.status,
            "plan_tier": subscription.plan_tier,
            "billing_cycle": subscription.billing_cycle,
            "currency": subscription.currency,
            "price_cents": subscription.price_cents,
            "latest_reference": subscription.latest_reference,
            "current_period_start": self._serialize_dt(subscription.current_period_start),
            "current_period_end": self._serialize_dt(subscription.current_period_end),
            "canceled_at": self._serialize_dt(subscription.canceled_at),
            "provider_customer_code": subscription.provider_customer_code,
            "provider_subscription_code": subscription.provider_subscription_code,
            "provider_plan_code": subscription.provider_plan_code,
            "can_cancel": bool(
                subscription.provider_subscription_code
                and subscription.provider_email_token
                and subscription.status in {"active", "past_due"}
            ),
        }

    async def cancel_subscription(self, org_id: UUID) -> dict[str, Any]:
        self._ensure_configured()
        subscription = await self._get_subscription_by_org(org_id)
        if not subscription:
            raise PaystackError("No subscription found for this organization")
        if not subscription.provider_subscription_code or not subscription.provider_email_token:
            raise PaystackError("Subscription cannot be canceled yet")

        await self._request(
            "POST",
            "/subscription/disable",
            json={
                "code": subscription.provider_subscription_code,
                "token": subscription.provider_email_token,
            },
        )
        subscription.status = "canceled"
        subscription.canceled_at = datetime.now(timezone.utc)
        await self.db.flush()
        return {
            "status": "canceled",
            "message": "Subscription cancellation was sent to Paystack.",
        }

    async def process_webhook_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        event_type = str(payload.get("event") or "")
        data = payload.get("data") or {}
        if event_type == "charge.success":
            reference = data.get("reference")
            if not reference:
                raise PaystackVerificationError("Missing reference on charge.success")
            return await self.verify_and_activate_checkout(str(reference))
        if event_type == "subscription.create":
            return await self._handle_subscription_create(data)
        if event_type in {"subscription.disable", "subscription.not_renew"}:
            return await self._handle_subscription_disable(data)
        if event_type == "invoice.payment_failed":
            return await self._handle_invoice_payment_failed(data)
        if event_type in {"invoice.create", "invoice.update"}:
            return await self._handle_invoice_update(data)
        return {"status": "ignored", "event": event_type}

    async def ensure_plan(self, tier: str, user_id: UUID | None = None) -> str:
        self._ensure_configured()
        amount_subunits = await self._get_tier_amount_subunits(tier)
        config_key = f"paystack_plan_{tier}"
        existing = await self.pricing_repo.get_config(config_key)
        if (
            isinstance(existing, dict)
            and existing.get("plan_code")
            and existing.get("amount_subunits") == amount_subunits
            and existing.get("currency") == self.CURRENCY
            and existing.get("interval") == self.BILLING_CYCLE
        ):
            return str(existing["plan_code"])

        label = tier.replace("_", " ").title()
        response = await self._request(
            "POST",
            "/plan",
            json={
                "name": f"Cogent {label}",
                "interval": self.BILLING_CYCLE,
                "amount": amount_subunits,
                "currency": self.CURRENCY,
                "description": f"Cogent {label} monthly plan",
            },
        )
        plan_code = response.get("plan_code")
        if not plan_code:
            raise PaystackError("Paystack did not return a plan code")

        await self.pricing_repo.update_config(
            config_key,
            {
                "plan_code": plan_code,
                "amount_subunits": amount_subunits,
                "currency": self.CURRENCY,
                "interval": self.BILLING_CYCLE,
            },
            user_id,
        )
        return str(plan_code)

    async def verify_transaction(self, reference: str) -> dict[str, Any]:
        self._ensure_configured()
        return await self._request("GET", f"/transaction/verify/{reference}")

    async def _handle_subscription_create(self, data: dict[str, Any]) -> dict[str, Any]:
        subscription = await self._find_subscription_for_event(data)
        if not subscription:
            return {"status": "ignored", "reason": "subscription_not_found"}

        subscription.provider = self.PROVIDER
        subscription.provider_customer_code = self._customer_code_from_event(data) or subscription.provider_customer_code
        subscription.provider_plan_code = self._plan_code_from_event(data) or subscription.provider_plan_code
        subscription.provider_subscription_code = data.get("subscription_code") or subscription.provider_subscription_code
        subscription.provider_email_token = data.get("email_token") or subscription.provider_email_token
        subscription.status = str(data.get("status") or subscription.status or "active")
        subscription.current_period_end = self._parse_dt(data.get("next_payment_date")) or subscription.current_period_end
        subscription.provider_metadata = self._merge_metadata(subscription.provider_metadata, {"subscription_create": data})
        await self.db.flush()
        return {"status": "processed", "event": "subscription.create"}

    async def _handle_subscription_disable(self, data: dict[str, Any]) -> dict[str, Any]:
        subscription = await self._find_subscription_for_event(data)
        if not subscription:
            return {"status": "ignored", "reason": "subscription_not_found"}

        subscription.status = "canceled"
        subscription.canceled_at = datetime.now(timezone.utc)
        subscription.provider_metadata = self._merge_metadata(subscription.provider_metadata, {"subscription_disable": data})
        await self.db.flush()
        return {"status": "processed", "event": "subscription.disable"}

    async def _handle_invoice_payment_failed(self, data: dict[str, Any]) -> dict[str, Any]:
        subscription = await self._find_subscription_for_event(data)
        if not subscription:
            return {"status": "ignored", "reason": "subscription_not_found"}

        subscription.status = "past_due"
        subscription.provider_metadata = self._merge_metadata(subscription.provider_metadata, {"invoice_payment_failed": data})
        await self.db.flush()
        return {"status": "processed", "event": "invoice.payment_failed"}

    async def _handle_invoice_update(self, data: dict[str, Any]) -> dict[str, Any]:
        subscription = await self._find_subscription_for_event(data)
        if not subscription:
            return {"status": "ignored", "reason": "subscription_not_found"}

        paid_at = self._parse_dt(data.get("paid_at"))
        next_payment_date = self._parse_dt(data.get("next_payment_date"))
        if paid_at:
            subscription.current_period_start = paid_at
            subscription.status = "active"
        if next_payment_date:
            subscription.current_period_end = next_payment_date
        subscription.provider_metadata = self._merge_metadata(subscription.provider_metadata, {"invoice_update": data})
        await self.db.flush()
        return {"status": "processed", "event": "invoice.update"}

    async def _find_subscription_for_event(self, data: dict[str, Any]) -> Subscription | None:
        subscription_code = data.get("subscription_code") or self._subscription_code_from_event(data)
        if subscription_code:
            result = await self.db.execute(
                select(Subscription).where(Subscription.provider_subscription_code == str(subscription_code))
            )
            match = result.scalar_one_or_none()
            if match:
                return match

        customer_code = self._customer_code_from_event(data)
        if customer_code:
            result = await self.db.execute(
                select(Subscription).where(Subscription.provider_customer_code == customer_code)
            )
            match = result.scalar_one_or_none()
            if match:
                return match

        reference = data.get("reference")
        if reference:
            result = await self.db.execute(
                select(Subscription).where(Subscription.latest_reference == str(reference))
            )
            return result.scalar_one_or_none()
        return None

    async def _get_or_create_subscription(self, org_id: UUID) -> Subscription:
        subscription = await self._get_subscription_by_org(org_id)
        if subscription:
            return subscription
        subscription = Subscription(
            org_id=org_id,
            plan_tier="explorer",
            billing_cycle=self.BILLING_CYCLE,
            currency=self.CURRENCY,
            status="inactive",
        )
        self.db.add(subscription)
        await self.db.flush()
        return subscription

    async def _get_subscription_by_org(self, org_id: UUID) -> Subscription | None:
        result = await self.db.execute(
            select(Subscription).where(Subscription.org_id == org_id)
        )
        return result.scalar_one_or_none()

    async def _get_tier_amount_subunits(self, tier: str) -> int:
        return await self.pricing_repo.get_tier_price(tier) * 100

    async def _request(self, method: str, path: str, *, json: dict[str, Any] | None = None) -> dict[str, Any]:
        self._ensure_configured()
        headers = {
            "Authorization": f"Bearer {self.settings.paystack_secret_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(
                base_url=self.settings.paystack_base_url.rstrip("/"),
                timeout=30.0,
            ) as client:
                response = await client.request(method, path, headers=headers, json=json)
        except httpx.HTTPError as exc:  # pragma: no cover
            raise PaystackError("Could not reach Paystack") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise PaystackError("Paystack returned an invalid response") from exc

        if response.status_code >= 400:
            detail = payload.get("message") if isinstance(payload, dict) else None
            raise PaystackError(detail or "Paystack request failed")
        if not payload.get("status"):
            raise PaystackError(str(payload.get("message") or "Paystack request failed"))
        data = payload.get("data")
        if not isinstance(data, dict):
            raise PaystackError("Paystack did not return a usable data payload")
        return data

    def _ensure_configured(self) -> None:
        if not self.settings.paystack_secret_key:
            raise PaystackConfigurationError("PAYSTACK_SECRET_KEY is not configured")

    @staticmethod
    def _build_reference(org_id: UUID, target_tier: str) -> str:
        return f"cogent_{str(org_id).replace('-', '')[:10]}_{target_tier}_{uuid4().hex[:12]}"

    @staticmethod
    def _coerce_metadata(metadata: Any) -> dict[str, Any]:
        if isinstance(metadata, dict):
            return metadata
        if isinstance(metadata, str):
            try:
                parsed = json.loads(metadata)
            except json.JSONDecodeError:
                return {}
            return parsed if isinstance(parsed, dict) else {}
        return {}

    @staticmethod
    def _merge_metadata(existing: Any, patch: dict[str, Any]) -> dict[str, Any]:
        merged = dict(existing or {})
        merged.update(patch)
        return merged

    @staticmethod
    def _serialize_dt(value: datetime | None) -> str | None:
        return value.isoformat() if value else None

    @staticmethod
    def _parse_dt(value: Any) -> datetime | None:
        if not value or not isinstance(value, str):
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    @staticmethod
    def _customer_code_from_event(data: dict[str, Any]) -> str | None:
        customer = data.get("customer")
        if isinstance(customer, dict) and customer.get("customer_code"):
            return str(customer["customer_code"])
        return None

    @staticmethod
    def _plan_code_from_event(data: dict[str, Any]) -> str | None:
        plan = data.get("plan")
        if isinstance(plan, dict) and plan.get("plan_code"):
            return str(plan["plan_code"])
        if data.get("plan_code"):
            return str(data["plan_code"])
        return None

    @staticmethod
    def _subscription_code_from_event(data: dict[str, Any]) -> str | None:
        subscription = data.get("subscription")
        if isinstance(subscription, dict) and subscription.get("subscription_code"):
            return str(subscription["subscription_code"])
        if isinstance(subscription, str):
            return subscription
        return None
