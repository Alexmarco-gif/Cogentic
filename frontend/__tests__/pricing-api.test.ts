import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  getSubscriptionStatus,
  getTierOptions,
  upgradeTier,
  verifyTierCheckout,
} from "@/lib/api/pricing";

function jsonResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? "OK" : "Error",
    headers: {
      get: vi.fn().mockReturnValue("application/json"),
    },
    json: vi.fn().mockResolvedValue(body),
    text: vi.fn().mockResolvedValue(JSON.stringify(body)),
  } as unknown as Response;
}

describe("pricing api", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("loads public tier options without auth", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({ tiers: [{ tier: "growth", price: 499 }] }),
      );
    vi.stubGlobal("fetch", fetchMock);

    const result = await getTierOptions();

    expect(result.tiers).toEqual([{ tier: "growth", price: 499 }]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/pricing/tiers",
      expect.objectContaining({
        method: "GET",
        headers: expect.not.objectContaining({
          Authorization: expect.any(String),
        }),
      }),
    );
  });

  it("initializes authenticated Paystack checkout for tier upgrades", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ token: "test-token" }))
      .mockResolvedValueOnce(
        jsonResponse({
          status: "checkout_initialized",
          requested_tier: "growth",
          message: "Secure Paystack checkout is ready.",
          reference: "cogent_ref_123",
          access_code: "access_123",
          authorization_url: "https://checkout.paystack.test",
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    const result = await upgradeTier({
      target_tier: "growth",
      callback_url:
        "https://example.com/dashboard/settings?tab=plan&paystack=return",
    });

    expect(result.status).toBe("checkout_initialized");
    expect(fetchMock).toHaveBeenNthCalledWith(1, "/api/auth/access-token");
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/pricing/upgrade",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          Authorization: "Bearer test-token",
        }),
        body: JSON.stringify({
          target_tier: "growth",
          callback_url:
            "https://example.com/dashboard/settings?tab=plan&paystack=return",
        }),
      }),
    );
  });

  it("verifies completed tier checkout references through the authenticated endpoint", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ token: "test-token" }))
      .mockResolvedValueOnce(
        jsonResponse({
          status: "activated",
          tier: "growth",
          message: "Growth is now active.",
          reference: "cogent_ref_123",
          transaction_status: "success",
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    const result = await verifyTierCheckout({ reference: "cogent_ref_123" });

    expect(result.status).toBe("activated");
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/pricing/verify",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ reference: "cogent_ref_123" }),
      }),
    );
  });

  it("loads authenticated subscription status", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ token: "test-token" }))
      .mockResolvedValueOnce(
        jsonResponse({
          provider: "paystack",
          status: "active",
          plan_tier: "growth",
          billing_cycle: "monthly",
          currency: "USD",
          price_cents: 49900,
          latest_reference: "cogent_ref_123",
          current_period_start: null,
          current_period_end: null,
          canceled_at: null,
          provider_customer_code: "CUS_123",
          provider_subscription_code: "SUB_123",
          provider_plan_code: "PLN_123",
          can_cancel: true,
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    const result = await getSubscriptionStatus();

    expect(result.provider).toBe("paystack");
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/pricing/subscription",
      expect.objectContaining({
        method: "GET",
      }),
    );
  });
});
