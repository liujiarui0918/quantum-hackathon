import type { PlaygroundSummaryEvent } from '@/lib/playground-types';

type Props = { event: PlaygroundSummaryEvent };

export function SummaryCard({ event }: Props) {
  return (
    <div style={{
      animation: 'fadeInUp 0.3s ease-out both',
      border: '1px solid var(--line)',
      borderLeft: '3px solid var(--accent)',
      borderRadius: '10px',
      padding: '14px 16px',
      background: '#ffffff',
      boxShadow: 'var(--shadow)',
    }}>
      <div style={{ fontSize: '10px', color: 'var(--accent)', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: '6px' }}>
        {event.phase}
      </div>
      <div style={{ fontSize: '14px', color: 'var(--text)', marginBottom: '8px', lineHeight: 1.5 }}>{event.message}</div>
      {event.highlights.length > 0 && (
        <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
          {event.highlights.map((h, i) => (
            <li key={i} style={{ fontSize: '13px', color: 'var(--muted)', paddingLeft: '14px', position: 'relative', marginBottom: '3px' }}>
              <span style={{ position: 'absolute', left: 0, top: '7px', width: '6px', height: '6px', borderRadius: '50%', background: 'var(--accent)' }} />
              {h}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
