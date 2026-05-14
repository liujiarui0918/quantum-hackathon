import type { PlaygroundEvent, PlaygroundStreamRequest, PlaygroundScript } from '@/lib/playground-types';
import { selectPlaygroundScript } from '@/lib/playground-mock/router';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function POST(request: Request): Promise<Response> {
  let prompt: string;
  try {
    const body = (await request.json()) as Partial<PlaygroundStreamRequest>;
    if (!body || typeof body.prompt !== 'string' || body.prompt.trim() === '') {
      return new Response(JSON.stringify({ error: 'missing prompt' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }
    prompt = body.prompt;
  } catch {
    return new Response(JSON.stringify({ error: 'invalid JSON body' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  const script = selectPlaygroundScript(prompt);
  const signal = request.signal;

  const stream = createSseStream(script, signal);

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream; charset=utf-8',
      'Cache-Control': 'no-cache, no-transform',
      'Connection': 'keep-alive',
      'X-Accel-Buffering': 'no',
    },
  });
}

function createSseStream(
  script: PlaygroundScript,
  signal: AbortSignal,
): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  let closed = false;

  return new ReadableStream<Uint8Array>({
    async start(controller) {
      const onAbort = () => {
        closed = true;
        try { controller.close(); } catch { /* already closed */ }
      };
      signal.addEventListener('abort', onAbort, { once: true });

      try {
        for (const timed of script.events) {
          if (closed || signal.aborted) break;

          await delay(timed.delay_ms, signal);

          if (closed || signal.aborted) break;

          const chunk = encoder.encode(formatSseEvent(timed.event));
          safeEnqueue(controller, chunk);
        }

        if (!closed && !signal.aborted) {
          closed = true;
          signal.removeEventListener('abort', onAbort);
          try { controller.close(); } catch { /* already closed */ }
        }
      } catch (err: unknown) {
        if (err instanceof DOMException && err.name === 'AbortError') {
          // Client cancelled — close silently
        } else {
          // Unexpected error — try to push an error event then close
          if (!closed) {
            const errorEvent: PlaygroundEvent = {
              type: 'error',
              code: 'stream_error',
              message: err instanceof Error ? err.message : 'Unknown stream error',
            };
            safeEnqueue(controller, encoder.encode(formatSseEvent(errorEvent)));
          }
        }
        closed = true;
        signal.removeEventListener('abort', onAbort);
        try { controller.close(); } catch { /* already closed */ }
      }
    },
  });

  function safeEnqueue(
    controller: ReadableStreamDefaultController<Uint8Array>,
    chunk: Uint8Array,
  ): void {
    if (closed || signal.aborted) return;
    try {
      controller.enqueue(chunk);
    } catch {
      closed = true;
    }
  }
}

function delay(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise<void>((resolve, reject) => {
    if (signal.aborted) {
      reject(new DOMException('Aborted', 'AbortError'));
      return;
    }
    const timer = setTimeout(() => {
      signal.removeEventListener('abort', onAbort);
      resolve();
    }, ms);
    const onAbort = () => {
      clearTimeout(timer);
      reject(new DOMException('Aborted', 'AbortError'));
    };
    signal.addEventListener('abort', onAbort, { once: true });
  });
}

function formatSseEvent(event: PlaygroundEvent): string {
  return `data: ${JSON.stringify(event)}\n\n`;
}
