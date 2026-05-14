import type { PlaygroundErrorEvent } from '@/lib/playground-types';

type Props = { event: PlaygroundErrorEvent };

export function ErrorCard({ event }: Props) {
  return (
    <div style={{
      animation: 'fadeInUp 0.3s ease-out both',
      border: '1px solid rgba(220, 53, 69, 0.25)',
      background: 'rgba(220, 53, 69, 0.04)',
      borderRadius: '10px',
      padding: '12px 16px',
      color: 'var(--danger)',
      fontSize: '13px',
      fontWeight: 500,
      boxShadow: 'var(--shadow)',
    }}>
      <strong>[{event.code}]</strong> {event.message}
    </div>
  );
}
