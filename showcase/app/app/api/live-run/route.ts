import { NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const MODAL_URL = process.env.PARLIAMENT_MODAL_RUN_URL;
const MODAL_AUTH_TOKEN = process.env.PARLIAMENT_MODAL_AUTH_TOKEN;
const MODAL_KEY = process.env.PARLIAMENT_MODAL_KEY;
const MODAL_SECRET = process.env.PARLIAMENT_MODAL_SECRET;

function modalHeaders() {
  const headers: Record<string, string> = {
    "content-type": "application/json",
  };
  if (MODAL_AUTH_TOKEN) headers.authorization = `Bearer ${MODAL_AUTH_TOKEN}`;
  if (MODAL_KEY) headers["Modal-Key"] = MODAL_KEY;
  if (MODAL_SECRET) headers["Modal-Secret"] = MODAL_SECRET;
  return headers;
}

export async function POST(request: Request) {
  if (!MODAL_URL) {
    return NextResponse.json(
      { error: "PARLIAMENT_MODAL_RUN_URL is not configured" },
      { status: 503 },
    );
  }

  const payload = await request.json().catch(() => ({}));
  const modalResponse = await fetch(MODAL_URL, {
    method: "POST",
    headers: modalHeaders(),
    body: JSON.stringify(payload),
    cache: "no-store",
  });

  const body = await modalResponse.text();
  return new NextResponse(body, {
    status: modalResponse.status,
    headers: {
      "content-type": modalResponse.headers.get("content-type") ?? "application/json",
      "cache-control": "no-store",
    },
  });
}
