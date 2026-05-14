import type { PlaygroundDoneEvent } from '@/lib/playground-types';

type Props = { event: PlaygroundDoneEvent };

export function DoneCard({ event }: Props) {
  return (
    <div style={{
      animation: 'fadeInUp 0.3s ease-out both',
      textAlign: 'center',
      color: 'var(--accent)',
      fontWeight: 700,
      fontSize: '15px',
      padding: '12px',
      border: '1px solid rgba(212, 160, 23, 0.2)',
      borderRadius: '10px',
      background: 'var(--gold-soft)',
      boxShadow: 'var(--shadow)',
    }}>
      {event.message}
    </div>
  );
}
