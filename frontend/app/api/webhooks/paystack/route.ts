import { NextRequest } from "next/server";

import {
  handlePaystackWebhook,
  paystackWebhookHealth,
} from "./_shared";

export async function POST(request: NextRequest) {
  return handlePaystackWebhook(request);
}

export async function GET() {
  return paystackWebhookHealth();
}
