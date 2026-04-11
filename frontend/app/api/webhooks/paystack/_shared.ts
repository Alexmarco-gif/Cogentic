import { NextRequest, NextResponse } from "next/server";

function backendUrl() {
  return (
    process.env.BACKEND_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://localhost:8000"
  );
}

async function forwardToBackend(
  rawBody: string,
  signature: string | null,
): Promise<Response> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (signature) {
    headers["x-paystack-signature"] = signature;
  }

  return fetch(`${backendUrl()}/webhooks/paystack/events`, {
    method: "POST",
    headers,
    body: rawBody,
    signal: AbortSignal.timeout(15_000),
  });
}

export async function handlePaystackWebhook(request: NextRequest) {
  try {
    const rawBody = await request.text();
    const signature = request.headers.get("x-paystack-signature");

    const response = await forwardToBackend(rawBody, signature);
    const text = await response.text();

    return new NextResponse(text, {
      status: response.status,
      headers: {
        "Content-Type": response.headers.get("content-type") || "application/json",
      },
    });
  } catch (error) {
    return NextResponse.json(
      {
        error: "Failed to forward Paystack webhook",
        detail: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 502 },
    );
  }
}

export async function paystackWebhookHealth() {
  return NextResponse.json({
    status: "ok",
    message: "Paystack webhook relay endpoint is active",
    backend_url: backendUrl(),
    timestamp: new Date().toISOString(),
  });
}
