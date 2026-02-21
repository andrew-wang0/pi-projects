import { readMessageState } from "@/lib/message-store";
import { subscribeMessageState } from "@/lib/message-stream";

export const runtime = "nodejs";

const encoder = new TextEncoder();
const STATE_TICK_INTERVAL_MS = 5_000;

function formatEventData(payload: unknown) {
  return encoder.encode(`data: ${JSON.stringify(payload)}\n\n`);
}

export function GET(request: Request) {
  let closed = false;
  let unsubscribe: (() => void) | null = null;
  let stateTickInterval: NodeJS.Timeout | null = null;

  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      const cleanup = () => {
        if (closed) {
          return;
        }

        closed = true;

        if (stateTickInterval) {
          clearInterval(stateTickInterval);
          stateTickInterval = null;
        }

        if (unsubscribe) {
          unsubscribe();
          unsubscribe = null;
        }
      };

      const pushLatestState = async () => {
        if (closed) {
          return;
        }

        const state = await readMessageState();

        try {
          controller.enqueue(formatEventData(state));
        } catch {
          cleanup();
        }
      };

      try {
        await pushLatestState();
      } catch {
        cleanup();
        controller.close();
        return;
      }

      unsubscribe = subscribeMessageState(() => {
        void pushLatestState().catch(() => {
          cleanup();
        });
      });

      stateTickInterval = setInterval(() => {
        if (closed) {
          return;
        }

        void pushLatestState().catch(() => {
          cleanup();
        });
      }, STATE_TICK_INTERVAL_MS);

      request.signal.addEventListener(
        "abort",
        () => {
          cleanup();
          controller.close();
        },
        { once: true },
      );
    },
    cancel() {
      closed = true;

      if (stateTickInterval) {
        clearInterval(stateTickInterval);
        stateTickInterval = null;
      }

      if (unsubscribe) {
        unsubscribe();
        unsubscribe = null;
      }
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
