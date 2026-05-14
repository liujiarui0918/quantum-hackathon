import type { PlaygroundOpenQuestionEvent } from '@/lib/playground-types';

type Props = { event: PlaygroundOpenQuestionEvent };

export function OpenQuestionCard({ event }: Props) {
  return (
    <div style={{
      animation: 'fadeInUp 0.3s ease-out both',
      border: '1px solid rgba(232, 89, 12, 0.2)',
      background: 'var(--orange-soft)',
      borderRadius: '10px',
      padding: '12px 16px',
      boxShadow: 'var(--shadow)',
    }}>
      <div style={{ fontSize: '10px', color: 'var(--accent2)', fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase' }}>{event.category}</div>
      <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--accent2)', margin: '4px 0' }}>{event.title}</div>
      <div style={{ fontSize: '13px', color: 'var(--muted)', lineHeight: 1.5 }}>{event.description}</div>
    </div>
  );
}
