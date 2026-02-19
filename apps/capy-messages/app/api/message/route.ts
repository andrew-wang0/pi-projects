import { NextResponse } from "next/server";

import {
  deleteScheduledMessage,
  readMessageState,
  saveActiveMessage,
  scheduleMessage,
} from "@/lib/message-store";
import { notifyMessageStateChanged } from "@/lib/message-stream";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  const state = await readMessageState();
  return NextResponse.json(state, {
    headers: {
      "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    },
  });
}

export async function PUT(request: Request) {
  try {
    const body = (await request.json()) as { message?: unknown; backgroundId?: unknown };

    if (typeof body.message !== "string") {
      return NextResponse.json({ error: "`message` must be a string." }, { status: 400 });
    }

    if (body.backgroundId !== undefined && typeof body.backgroundId !== "string") {
      return NextResponse.json({ error: "`backgroundId` must be a string." }, { status: 400 });
    }

    const state = await saveActiveMessage(body.message, body.backgroundId);
    notifyMessageStateChanged();
    return NextResponse.json(state);
  } catch {
    return NextResponse.json({ error: "Unable to save message." }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as {
      message?: unknown;
      startAt?: unknown;
      backgroundId?: unknown;
    };

    if (typeof body.message !== "string" || typeof body.startAt !== "string") {
      return NextResponse.json(
        { error: "`message` and `startAt` must both be strings." },
        { status: 400 },
      );
    }

    if (body.backgroundId !== undefined && typeof body.backgroundId !== "string") {
      return NextResponse.json({ error: "`backgroundId` must be a string." }, { status: 400 });
    }

    const state = await scheduleMessage(body.message, body.startAt, body.backgroundId);
    notifyMessageStateChanged();
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
  notifyMessageStateChanged();
  return NextResponse.json(state);
}
