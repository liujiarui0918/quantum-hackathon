import type { PlaygroundFinalEvent } from '@/lib/playground-types';
import { SimulatedBadge } from '../SimulatedBadge';

type Props = { event: PlaygroundFinalEvent };

export function FinalCard({ event }: Props) {
  const sol = event.best_solution;

  return (
    <div style={{
      animation: 'fadeInUp 0.3s ease-out both',
      border: '1px solid rgba(212, 160, 23, 0.25)',
      background: '#ffffff',
      borderRadius: '12px',
      padding: '16px',
      boxShadow: '0 4px 16px rgba(212, 160, 23, 0.08)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
        <span style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text)' }}>最终优化方案</span>
        <SimulatedBadge />
      </div>

      <div style={{ fontSize: '11px', color: 'var(--muted)', fontWeight: 600, marginBottom: '2px' }}>objective_value</div>
      <div style={{ fontSize: '36px', fontWeight: 800, color: 'var(--accent)', letterSpacing: '-0.02em', lineHeight: 1.1 }}>{sol.objective_value}</div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: '10px', marginTop: '14px' }}>
        <div style={{ padding: '10px 12px', borderRadius: '10px', background: 'var(--bg1)', border: '1px solid var(--line)' }}>
          <div style={{ fontSize: '10px', color: 'var(--muted)', fontWeight: 600, marginBottom: '2px' }}>bitstring</div>
          <div style={{ fontSize: '14px', color: 'var(--text)', fontVariantNumeric: 'tabular-nums', fontFamily: "'SF Mono','Cascadia Code',monospace" }}>{sol.bitstring}</div>
        </div>
        <div style={{ padding: '10px 12px', borderRadius: '10px', background: 'var(--bg1)', border: '1px solid var(--line)' }}>
          <div style={{ fontSize: '10px', color: 'var(--muted)', fontWeight: 600, marginBottom: '2px' }}>feasible</div>
          <div style={{ fontSize: '18px', fontWeight: 700, color: sol.is_feasible ? '#16a34a' : 'var(--danger)' }}>{String(sol.is_feasible)}</div>
        </div>
        <div style={{ padding: '10px 12px', borderRadius: '10px', background: 'var(--bg1)', border: '1px solid var(--line)' }}>
          <div style={{ fontSize: '10px', color: 'var(--muted)', fontWeight: 600, marginBottom: '2px' }}>source_backend</div>
          <div style={{ fontSize: '14px', color: 'var(--text)', fontWeight: 600 }}>{sol.source_backend}</div>
        </div>
        <div style={{ padding: '10px 12px', borderRadius: '10px', background: 'var(--bg1)', border: '1px solid var(--line)' }}>
          <div style={{ fontSize: '10px', color: 'var(--muted)', fontWeight: 600, marginBottom: '2px' }}>qaoa_backend</div>
          <div style={{ fontSize: '11px', color: 'var(--text)', wordBreak: 'break-all' }}>{event.qaoa_backend}</div>
        </div>
      </div>

      {/* Logical solution */}
      <div style={{ marginTop: '12px' }}>
        <div style={{ fontSize: '10px', color: 'var(--muted)', fontWeight: 600, marginBottom: '4px' }}>logical_solution</div>
        <pre style={{
          margin: 0, padding: '10px 12px', borderRadius: '8px', background: 'var(--bg1)',
          border: '1px solid var(--line)',
          fontSize: '12px', fontFamily: "'SF Mono','Cascadia Code','Fira Code',monospace",
          color: 'var(--text)',
        }}>
          {JSON.stringify(sol.logical_solution, null, 2)}
        </pre>
      </div>

      {/* Benchmark table */}
      {event.benchmark.rows.length > 0 && (
        <table style={{ width: '100%', marginTop: '14px', borderCollapse: 'collapse', fontSize: '12px' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid var(--line)' }}>
              <th style={{ textAlign: 'left', color: 'var(--muted)', fontWeight: 600, padding: '8px 6px' }}>solver</th>
              <th style={{ textAlign: 'left', color: 'var(--muted)', fontWeight: 600, padding: '8px 6px' }}>status</th>
              <th style={{ textAlign: 'left', color: 'var(--muted)', fontWeight: 600, padding: '8px 6px' }}>obj</th>
              <th style={{ textAlign: 'left', color: 'var(--muted)', fontWeight: 600, padding: '8px 6px' }}>ratio</th>
              <th style={{ textAlign: 'left', color: 'var(--muted)', fontWeight: 600, padding: '8px 6px' }}>ms</th>
            </tr>
          </thead>
          <tbody>
            {event.benchmark.rows.map((row) => (
              <tr key={row.solver} style={{ borderBottom: '1px solid var(--line)' }}>
                <td style={{ padding: '8px 6px', color: 'var(--text)', fontVariantNumeric: 'tabular-nums', fontWeight: 500 }}>{row.solver}</td>
                <td style={{ padding: '8px 6px', color: row.status === 'ran' ? '#16a34a' : 'var(--muted)', fontWeight: 600 }}>{row.status}</td>
                <td style={{ padding: '8px 6px', fontVariantNumeric: 'tabular-nums', fontWeight: 600, fontSize: '16px', color: 'var(--accent)' }}>{row.best_feasible_objective ?? '-'}</td>
                <td style={{ padding: '8px 6px', fontVariantNumeric: 'tabular-nums', color: 'var(--muted)' }}>{row.feasible_sample_ratio != null ? row.feasible_sample_ratio.toFixed(3) : '-'}</td>
                <td style={{ padding: '8px 6px', fontVariantNumeric: 'tabular-nums', color: 'var(--muted)' }}>{row.total_ms}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
