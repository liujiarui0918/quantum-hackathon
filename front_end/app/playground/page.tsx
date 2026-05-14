'use client';

import { useReducer, useRef, useEffect, useCallback, useState } from 'react';
import type { PlaygroundEvent } from '@/lib/playground-types';
import { listPlaygroundHistory, pushPlaygroundHistory } from '@/lib/playground-history';
import type { PlaygroundHistoryItem } from '@/lib/playground-history';
import { Banner } from './_components/Banner';
import { HistorySidebar } from './_components/HistorySidebar';
import { ChatInput } from './_components/ChatInput';
import { EventStream } from './_components/EventStream';
import styles from './playground.module.css';

type State = {
  events: PlaygroundEvent[];
  isStreaming: boolean;
  input: string;
  error: string | null;
};

type Action =
  | { type: 'append'; event: PlaygroundEvent }
  | { type: 'set_input'; value: string }
  | { type: 'start_stream' }
  | { type: 'stop_stream' }
  | { type: 'reset' }
  | { type: 'error'; message: string };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'append':
      return { ...state, events: [...state.events, action.event] };
    case 'set_input':
      return { ...state, input: action.value };
    case 'start_stream':
      return { ...state, isStreaming: true, error: null };
    case 'stop_stream':
      return { ...state, isStreaming: false };
    case 'reset':
      return { ...state, events: [], isStreaming: false, error: null };
    case 'error':
      return { ...state, isStreaming: false, error: action.message };
  }
}

export default function PlaygroundPage() {
  const [state, dispatch] = useReducer(reducer, {
    events: [],
    isStreaming: false,
    input: '',
    error: null,
  });

  const abortRef = useRef<AbortController | null>(null);
  const [history, setHistory] = useState<PlaygroundHistoryItem[]>([]);

  // Load history on mount (SSR-safe)
  useEffect(() => {
    setHistory(listPlaygroundHistory());
  }, []);

  const refreshHistory = useCallback(() => {
    setHistory(listPlaygroundHistory());
  }, []);

  const submit = useCallback(() => {
    if (state.isStreaming || !state.input.trim()) return;

    // Abort any existing stream
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }

    const ac = new AbortController();
    abortRef.current = ac;

    dispatch({ type: 'reset' });
    dispatch({ type: 'start_stream' });

    const prompt = state.input;

    fetch('/api/playground/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
      },
      body: JSON.stringify({ prompt }),
      signal: ac.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          dispatch({ type: 'error', message: `流连接中断，请重试 (HTTP ${response.status})` });
          return;
        }
        if (!response.body) {
          dispatch({ type: 'error', message: '流连接中断，请重试' });
          return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // Split on \n\n (SSE frame boundary)
          const parts = buffer.split('\n\n');
          buffer = parts.pop() ?? ''; // keep incomplete tail

          for (const part of parts) {
            const trimmed = part.trim();
            if (!trimmed) continue;

            for (const line of trimmed.split('\n')) {
              if (!line.startsWith('data: ')) continue;
              const jsonStr = line.slice(6);
              try {
                const event = JSON.parse(jsonStr) as PlaygroundEvent;
                dispatch({ type: 'append', event });

                if (event.type === 'done') {
                  dispatch({ type: 'stop_stream' });

                  // Save to history — use the event data itself since state.events is stale in closure
                  const title = prompt.slice(0, 40);
                  pushPlaygroundHistory({
                    id: Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 6),
                    prompt,
                    scenario: 'sample_assignment',
                    title,
                    created_at: new Date().toISOString(),
                  });
                  refreshHistory();
                }
              } catch {
                // malformed JSON — skip
              }
            }
          }
        }

        // Stream ended without done event
        dispatch({ type: 'stop_stream' });
      })
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === 'AbortError') {
          // Client cancelled — silent
          dispatch({ type: 'stop_stream' });
        } else {
          dispatch({ type: 'error', message: err instanceof Error ? err.message : 'Unknown error' });
        }
      });
  }, [state.input, state.isStreaming, refreshHistory]);

  const stop = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    dispatch({ type: 'stop_stream' });
  }, []);

  const handleHistorySelect = useCallback((item: PlaygroundHistoryItem) => {
    dispatch({ type: 'set_input', value: item.prompt });
  }, []);

  return (
    <div className={styles.shell}>
      <Banner />

      <HistorySidebar items={history} onSelect={handleHistorySelect} />

      <div className={styles.main}>
        <EventStream events={state.events} />

        {state.error && (
          <div className={styles.errorCard}>
            {state.error}
          </div>
        )}

        <div className={styles.inputArea}>
          <ChatInput
            value={state.input}
            onChange={(v) => dispatch({ type: 'set_input', value: v })}
            onSubmit={submit}
            onStop={stop}
            isStreaming={state.isStreaming}
          />
          <div className={styles.inputControls}>
            <div className={styles.kbdHint}>
              <kbd>Shift + Enter</kbd> 换行，<kbd>Enter</kbd> 发送
            </div>
            <button
              type="button"
              className="btn"
              style={{ minWidth: 100, background: 'var(--accent)', color: '#fff', borderColor: 'var(--accent)' }}
              onClick={submit}
              disabled={state.isStreaming || !state.input.trim()}
            >
              {state.isStreaming ? '分析中...' : '发送'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}