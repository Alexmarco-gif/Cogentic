"use client";

import Script from "next/script";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  AlertTriangle,
  Building2,
  Check,
  Loader2,
  ShieldCheck,
  Star,
  TrendingUp,
  Zap,
} from "lucide-react";

import {
  cancelSubscription,
  getSubscriptionStatus,
  getTierOptions,
  upgradeTier,
  verifyTierCheckout,
} from "@/lib/api/pricing";
import { friendlyErrorMessage } from "@/lib/api/errors";
import { usePricing } from "@/lib/contexts/PricingContext";
import type {
  BillingSubscriptionResponse,
  TierUpgradeResponse,
} from "@/lib/api/types";

interface TierCard {
  id: string;
  name: string;
  icon: ReactNode;
  description: string;
  features: string[];
}

const TIER_COPY: TierCard[] = [
  {
    id: "explorer",
    name: "Explorer",
    icon: <TrendingUp className="h-4 w-4 text-slate-400" />,
    description:
      "Free workspace for individual research, lightweight monitoring, and trial onboarding.",
    features: [
      "Core dashboard access",
      "Limited signal monitoring",
      "Starter monthly credits",
      "Single-workspace setup",
    ],
  },
  {
    id: "growth",
    name: "Growth",
    icon: <Zap className="h-4 w-4 text-primary" />,
    description:
      "Best fit for teams that need continuous signals, investigations, and API access.",
    features: [
      "Continuous intelligence feed",
      "On-demand investigations",
      "API key management",
      "Higher monthly credit allocation",
    ],
  },
  {
    id: "mid_market",
    name: "Mid-Market",
    icon: <Star className="h-4 w-4 text-amber-500" />,
    description:
      "Adds custom contracts, compliance workflows, and broader operational visibility.",
    features: [
      "Custom contracts",
      "Compliance modules",
      "Advanced exports",
      "Higher usage ceilings",
    ],
  },
  {
    id: "enterprise",
    name: "Enterprise",
    icon: <Building2 className="h-4 w-4 text-indigo-400" />,
    description:
      "For private deployments, dedicated support, and large-scale intelligence operations.",
    features: [
      "Private signal store",
      "Dedicated support and SLAs",
      "Custom deployment options",
      "Enterprise-grade limits",
    ],
  },
];

const EMPTY_SUBSCRIPTION: BillingSubscriptionResponse = {
  provider: null,
  status: null,
  plan_tier: null,
  billing_cycle: null,
  currency: null,
  price_cents: null,
  latest_reference: null,
  current_period_start: null,
  current_period_end: null,
  canceled_at: null,
  provider_customer_code: null,
  provider_subscription_code: null,
  provider_plan_code: null,
  can_cancel: false,
};

function currency(amount: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(amount);
}

function centsToCurrency(amount: number | null) {
  if (amount === null) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(amount / 100);
}

export function PlanSection() {
  const searchParams = useSearchParams();
  const { tier, credits, error: pricingError, refresh } = usePricing();

  const [tiers, setTiers] = useState<Array<{ tier: string; price: number }>>(
    [],
  );
  const [loading, setLoading] = useState(true);
  const [subscriptionLoading, setSubscriptionLoading] = useState(true);
  const [popupReady, setPopupReady] = useState(false);
  const [actionTier, setActionTier] = useState<string | null>(null);
  const [verifyingReference, setVerifyingReference] = useState<string | null>(
    null,
  );
  const [canceling, setCanceling] = useState(false);
  const [subscription, setSubscription] =
    useState<BillingSubscriptionResponse>(EMPTY_SUBSCRIPTION);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadPlanData() {
      setLoading(true);
      try {
        const response = await getTierOptions();
        if (!cancelled) setTiers(response.tiers);
      } catch (err) {
        if (!cancelled) setError(friendlyErrorMessage(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void loadPlanData();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadSubscription() {
      setSubscriptionLoading(true);
      try {
        const response = await getSubscriptionStatus({ graceful: true });
        if (!cancelled && response) setSubscription(response);
      } catch {
        if (!cancelled) setSubscription(EMPTY_SUBSCRIPTION);
      } finally {
        if (!cancelled) setSubscriptionLoading(false);
      }
    }

    void loadSubscription();
    return () => {
      cancelled = true;
    };
  }, []);

  const tierCards = useMemo(
    () =>
      TIER_COPY.map((card) => ({
        ...card,
        price: tiers.find((tierItem) => tierItem.tier === card.id)?.price ?? 0,
        isCurrent: tier === card.id,
      })),
    [tier, tiers],
  );

  async function refreshBillingState() {
    const [subscriptionResponse] = await Promise.all([
      getSubscriptionStatus({ graceful: true }),
      refresh(),
    ]);
    if (subscriptionResponse) setSubscription(subscriptionResponse);
  }

  async function verifyReference(reference: string, successMessage?: string) {
    if (!reference) return;

    setVerifyingReference(reference);
    setError(null);
    if (successMessage) setMessage(successMessage);

    try {
      const result = await verifyTierCheckout({ reference });
      setMessage(result.message);
      await refreshBillingState();

      const url = new URL(window.location.href);
      url.searchParams.delete("paystack");
      url.searchParams.delete("reference");
      url.searchParams.delete("trxref");
      window.history.replaceState({}, "", url.toString());
    } catch (err) {
      setError(friendlyErrorMessage(err));
    } finally {
      setVerifyingReference(null);
    }
  }

  useEffect(() => {
    const reference =
      searchParams.get("reference") ?? searchParams.get("trxref");
    const cameFromPaystack = searchParams.get("paystack") === "return";

    if (cameFromPaystack && reference && verifyingReference !== reference) {
      void verifyReference(reference, "Finalizing your payment…");
    }
  }, [searchParams, verifyingReference]);

  function openPaystackPopup(response: TierUpgradeResponse) {
    const popupCtor =
      typeof window !== "undefined" ? window.PaystackPop : undefined;

    if (popupCtor && response.access_code) {
      const popup = new popupCtor();
      popup.resumeTransaction(response.access_code, {
        onSuccess: (transaction) => {
          const reference =
            transaction.reference ?? transaction.trxref ?? response.reference;
          if (reference)
            void verifyReference(
              reference,
              "Payment received. Verifying your subscription…",
            );
        },
        onCancel: () => {
          setMessage("Checkout was closed before payment completed.");
        },
      });
      return;
    }

    if (response.authorization_url) {
      window.location.assign(response.authorization_url);
      return;
    }

    setError("Paystack checkout could not be opened. Please try again.");
  }

  async function handleUpgrade(targetTier: string) {
    if (targetTier === tier) return;

    setActionTier(targetTier);
    setError(null);
    setMessage(null);

    try {
      const callbackUrl =
        process.env.NEXT_PUBLIC_PAYSTACK_CALLBACK_URL?.trim() ||
        `${window.location.origin}/dashboard/settings?tab=plan&paystack=return`;
      const response = await upgradeTier({
        target_tier: targetTier,
        callback_url: callbackUrl,
      });
      setMessage("Secure checkout is ready.");
      openPaystackPopup(response);
    } catch (err) {
      setError(friendlyErrorMessage(err));
    } finally {
      setActionTier(null);
    }
  }

  async function handleCancelSubscription() {
    setCanceling(true);
    setError(null);
    setMessage(null);

    try {
      const response = await cancelSubscription();
      setMessage(response.message);
      await refreshBillingState();
    } catch (err) {
      setError(friendlyErrorMessage(err));
    } finally {
      setCanceling(false);
    }
  }

  const activeSubscription = Boolean(subscription.status);
  const creditsExhausted = credits.remaining <= 0;
  const creditsRunningLow = !creditsExhausted && credits.remaining <= 100;

  return (
    <div className="flex flex-col gap-8">
      <Script
        src="https://js.paystack.co/v2/inline.js"
        strategy="afterInteractive"
        onLoad={() => setPopupReady(true)}
        onError={() =>
          setError("The Paystack checkout script could not be loaded.")
        }
      />

      <div className="rounded-[28px] border border-border bg-surface p-6 shadow-card">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h2 className="text-xl font-medium text-heading">Plan and credit runway</h2>
            <p className="mt-1 text-sm text-subtle">
              Review your active tier, watch credit headroom, and upgrade only when your workspace needs more capacity.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <div className="rounded-xl border border-border bg-muted/30 px-4 py-3">
              <p className="text-[10px] uppercase tracking-wide text-subtle">
                Current tier
              </p>
              <p className="mt-1 text-sm font-semibold capitalize text-heading">
                {tier.replace("_", " ")}
              </p>
            </div>
            <div className="rounded-xl border border-border bg-muted/30 px-4 py-3">
              <p className="text-[10px] uppercase tracking-wide text-subtle">
                Credits used
              </p>
              <p className="mt-1 text-sm font-semibold text-heading">
                {credits.consumed.toLocaleString()}
              </p>
            </div>
            <div className="rounded-xl border border-border bg-muted/30 px-4 py-3">
              <p className="text-[10px] uppercase tracking-wide text-subtle">
                Credits remaining
              </p>
              <p className="mt-1 text-sm font-semibold text-heading">
                {credits.remaining.toLocaleString()}
              </p>
            </div>
          </div>
        </div>

        <div className="mt-5 flex flex-wrap items-center gap-3 text-xs text-subtle">
          <span className="inline-flex items-center gap-1 rounded-full border border-border bg-muted/30 px-3 py-1">
            <ShieldCheck className="h-3.5 w-3.5" />
            Secure checkout verification
          </span>
          <span className="inline-flex items-center gap-1 rounded-full border border-border bg-muted/30 px-3 py-1">
            {popupReady ? "Paystack ready" : "Preparing checkout"}
          </span>
          {verifyingReference && (
            <span className="inline-flex items-center gap-1 rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-primary">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Verifying {verifyingReference.slice(0, 12)}…
            </span>
          )}
        </div>

        {(message || error || pricingError) && (
          <div
            className={`mt-5 rounded-xl border px-4 py-3 text-sm ${
              error || pricingError
                ? "border-rose-200 bg-rose-50 text-rose-700"
                : "border-emerald-200 bg-emerald-50 text-emerald-700"
            }`}
          >
            {error ?? pricingError ?? message}
          </div>
        )}

        {creditsExhausted && (
          <div className="mt-4 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            <div className="flex items-start gap-3">
              <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
              <div>
                <p className="font-semibold">You are out of credits.</p>
                <p className="mt-1 text-amber-800">
                  Paid actions are blocked until your next renewal or a successful plan change.
                </p>
              </div>
            </div>
          </div>
        )}

        {creditsRunningLow && (
          <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50/70 px-4 py-3 text-sm text-amber-900">
            <div className="flex items-start gap-3">
              <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
              <div>
                <p className="font-semibold">Credits are running low.</p>
                <p className="mt-1 text-amber-800">
                  You have {credits.remaining.toLocaleString()} credits left before paid actions pause.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="rounded-[28px] border border-border bg-surface p-6 shadow-card">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h3 className="text-sm font-semibold text-heading">
              Subscription status
            </h3>
            <p className="mt-1 text-xs text-subtle">
              Current workspace billing state as reported by the payment processor.
            </p>
          </div>
          {subscription.can_cancel && (
            <button
              onClick={() => {
                void handleCancelSubscription();
              }}
              disabled={canceling}
              className="rounded-xl border border-border bg-surface px-4 py-2 text-[13px] font-semibold text-body transition-colors hover:bg-muted disabled:opacity-50"
            >
              {canceling ? "Canceling…" : "Cancel subscription"}
            </button>
          )}
        </div>

        {subscriptionLoading ? (
          <div className="mt-4 flex items-center gap-2 text-sm text-subtle">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading subscription state...
          </div>
        ) : activeSubscription ? (
          <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-xl border border-border bg-muted/30 px-4 py-3">
              <p className="text-[10px] uppercase tracking-wide text-subtle">
                Provider
              </p>
              <p className="mt-1 text-sm font-semibold capitalize text-heading">
                {subscription.provider ?? "—"}
              </p>
            </div>
            <div className="rounded-xl border border-border bg-muted/30 px-4 py-3">
              <p className="text-[10px] uppercase tracking-wide text-subtle">
                Status
              </p>
              <p className="mt-1 text-sm font-semibold capitalize text-heading">
                {subscription.status?.replace("_", " ") ?? "—"}
              </p>
            </div>
            <div className="rounded-xl border border-border bg-muted/30 px-4 py-3">
              <p className="text-[10px] uppercase tracking-wide text-subtle">
                Current billing
              </p>
              <p className="mt-1 text-sm font-semibold text-heading">
                {centsToCurrency(subscription.price_cents)}
              </p>
            </div>
            <div className="rounded-xl border border-border bg-muted/30 px-4 py-3">
              <p className="text-[10px] uppercase tracking-wide text-subtle">
                Renews / ends
              </p>
              <p className="mt-1 text-sm font-semibold text-heading">
                {subscription.current_period_end
                  ? new Date(
                      subscription.current_period_end,
                    ).toLocaleDateString()
                  : "Awaiting sync"}
              </p>
            </div>
          </div>
        ) : (
          <div className="mt-5 rounded-xl border border-dashed border-border bg-muted/20 px-4 py-4 text-sm text-subtle">
            No active paid subscription yet. Once payment is confirmed, billing status will appear here.
          </div>
        )}
      </div>

      {loading ? (
        <div className="flex items-center gap-2 text-sm text-subtle">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading plan options...
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-4">
          {tierCards.map((card) => (
            <div
              key={card.id}
              className={`relative flex flex-col rounded-[28px] border p-5 shadow-card transition-transform duration-200 ${
                card.isCurrent
                  ? "border-primary/40 bg-primary/5 ring-2 ring-primary/10"
                  : "border-border bg-surface hover:-translate-y-0.5"
              }`}
            >
              {card.id === "growth" && !card.isCurrent && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-full border border-primary/20 bg-primary px-3 py-0.5 text-[11px] font-semibold text-white">
                  Most Popular
                </div>
              )}

              <div className="mb-4">
                <div className="mb-1 flex items-center gap-2">
                  {card.icon}
                  <p className="text-sm font-semibold text-heading">
                    {card.name}
                  </p>
                </div>
                <div className="flex items-end gap-1">
                  <span className="text-2xl font-bold text-heading">
                    {currency(card.price)}
                  </span>
                  <span className="mb-0.5 text-xs text-subtle">/month</span>
                </div>
                <p className="mt-2 text-[11px] leading-relaxed text-subtle">
                  {card.description}
                </p>
              </div>

              <ul className="mb-6 flex flex-1 flex-col gap-2">
                {card.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-2">
                    <Check
                      className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-emerald-500"
                      strokeWidth={2.5}
                    />
                    <span className="text-[11px] leading-snug text-body">
                      {feature}
                    </span>
                  </li>
                ))}
              </ul>

              <button
                onClick={() => {
                  void handleUpgrade(card.id);
                }}
                disabled={
                  card.isCurrent ||
                  actionTier === card.id ||
                  verifyingReference !== null
                }
                className={`button-press w-full rounded-[18px] px-4 py-3 text-[13px] font-semibold transition-all ${
                  card.isCurrent
                    ? "cursor-not-allowed border border-primary/20 bg-primary/10 text-primary"
                    : "bg-primary text-white shadow-[0_18px_40px_-24px_rgba(37,99,235,0.7)] hover:-translate-y-0.5 hover:bg-primary-hover disabled:opacity-50"
                }`}
              >
                {actionTier === card.id
                  ? "Opening checkout…"
                  : card.isCurrent
                    ? "Current plan"
                    : `Upgrade to ${card.name}`}
              </button>

              {!card.isCurrent && (
                <p className="mt-3 text-[11px] text-subtle">
                  Secure inline checkout opens first. If your browser blocks it, we redirect to Paystack.
                </p>
              )}
            </div>
          ))}
        </div>
      )}

    </div>
  );
}
