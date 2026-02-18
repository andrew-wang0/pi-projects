import { NextResponse } from "next/server";

import {
  deleteScheduledMessage,
  readMessageState,
  saveActiveMessage,
  scheduleMessage,
} from "@/lib/message-store";

export const runtime = "nodejs";

export async function GET() {
  const state = await readMessageState();
  return NextResponse.json(state);
}

export async function PUT(request: Request) {
  try {
    const body = (await request.json()) as { message?: unknown };

    if (typeof body.message !== "string") {
      return NextResponse.json({ error: "`message` must be a string." }, { status: 400 });
    }

    const state = await saveActiveMessage(body.message);
    return NextResponse.json(state);
  } catch {
    return NextResponse.json({ error: "Unable to save message." }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as { message?: unknown; startAt?: unknown };

    if (typeof body.message !== "string" || typeof body.startAt !== "string") {
      return NextResponse.json(
        { error: "`message` and `startAt` must both be strings." },
        { status: 400 },
      );
    }

    const state = await scheduleMessage(body.message, body.startAt);
    return NextResponse.json(state);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unable to schedule message.";
    return NextResponse.json({ error: message }, { status: 400 });
  }
}

export async function DELETE(request: Request) {
  const { searchParams } = new URL(request.url);
  const id = searchParams.get("id");

  if (!id) {
    return NextResponse.json({ error: "`id` is required." }, { status: 400 });
  }

  const state = await deleteScheduledMessage(id);
  return NextResponse.json(state);
}
