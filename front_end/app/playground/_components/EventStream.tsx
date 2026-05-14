import type { PlaygroundEvent } from '@/lib/playground-types';
import { ThinkingCard } from './cards/ThinkingCard';
import { ToolCallCard } from './cards/ToolCallCard';
import { SummaryCard } from './cards/SummaryCard';
import { FinalCard } from './cards/FinalCard';
import { OpenQuestionCard } from './cards/OpenQuestionCard';
import { DoneCard } from './cards/DoneCard';
import { ErrorCard } from './cards/ErrorCard';

type Props = {
  events: PlaygroundEvent[];
};

export function EventStream({ events }: Props) {
  const merged = mergeToolEvents(events);

  return (
    <div style={{
      flex: 1,
      overflowY: 'auto',
      padding: '12px',
      display: 'flex',
      flexDirection: 'column',
      gap: '8px',
      borderRadius: '12px',
      background: '#ffffff',
      border: '1px solid var(--line)',
      boxShadow: 'var(--shadow)',
      minHeight: '300px',
      maxHeight: 'calc(100vh - 260px)',
    }}>
      {events.length === 0 && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flex: 1,
          color: 'var(--muted)',
          fontSize: '14px',
        }}>
          准备就绪，请输入优化问题开始探索
        </div>
      )}
      {merged.map((item, idx) => {
        if ('merged' in item) {
          return <ToolCallCard key={`tc-${item.call_id}`} call={item.call} result={item.result} />;
        }
        const event = item.event;
        switch (event.type) {
          case 'thinking':
            return <ThinkingCard key={`t-${idx}`} event={event} />;
          case 'summary':
            return <SummaryCard key={`s-${idx}`} event={event} />;
          case 'final':
            return <FinalCard key={`f-${idx}`} event={event} />;
          case 'open_question':
            return <OpenQuestionCard key={`oq-${idx}`} event={event} />;
          case 'done':
            return <DoneCard key={`d-${idx}`} event={event} />;
          case 'error':
            return <ErrorCard key={`e-${idx}`} event={event} />;
          case 'tool_call':
            return <ToolCallCard key={`tc-${idx}`} call={event} result={null} />;
          case 'tool_result':
            return null;
          default: {
            const _exhaustive: never = event;
            return null;
          }
        }
      })}
    </div>
  );
}

type MergedToolItem = { merged: true; call_id: string; call: import('@/lib/playground-types').PlaygroundToolCallEvent; result: import('@/lib/playground-types').PlaygroundToolResultEvent | null };
type SingleItem = { event: PlaygroundEvent };
type StreamItem = MergedToolItem | SingleItem;

function mergeToolEvents(events: PlaygroundEvent[]): StreamItem[] {
  const result: StreamItem[] = [];
  const emitted = new Set<string>();

  for (const event of events) {
    if (event.type === 'tool_call') {
      const nextIdx = events.indexOf(event) + 1;
      const nextEvent = nextIdx < events.length ? events[nextIdx] : null;
      const matchResult = nextEvent && nextEvent.type === 'tool_result' && nextEvent.call_id === event.call_id
        ? nextEvent : null;
      result.push({ merged: true, call_id: event.call_id, call: event, result: matchResult });
      emitted.add(event.call_id);
      if (matchResult) emitted.add(matchResult.call_id);
    } else if (event.type === 'tool_result') {
      if (!emitted.has(event.call_id)) {
        result.push({ event });
      }
    } else {
      result.push({ event });
    }
  }

  return result;
}
