import type { PlaygroundThinkingEvent } from '@/lib/playground-types';

type Props = { event: PlaygroundThinkingEvent };

export function ThinkingCard({ event }: Props) {
  return (
    <div style={{
      animation: 'fadeInUp 0.3s ease-out both',
      border: '1px solid var(--line)',
      borderRadius: '10px',
      padding: '12px 16px',
      background: '#ffffff',
      boxShadow: 'var(--shadow)',
      display: 'flex',
      alignItems: 'center',
      gap: '10px',
      fontSize: '14px',
      color: 'var(--muted)',
    }}>
      <span style={{ fontWeight: 600, color: 'var(--accent)' }}>AI 正在思考</span>
      <span>{event.message}</span>
    </div>
  );
}
