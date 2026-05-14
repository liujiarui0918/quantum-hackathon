'use client';

import type { PlaygroundBenchmarkRow } from '@/lib/playground-types';

interface Props {
  rows: PlaygroundBenchmarkRow[];
  sense: 'minimize' | 'maximize';
}

const WRAP_STYLE: React.CSSProperties = {
  border: '1px solid var(--line, #e5e5e7)',
  borderRadius: 16,
  padding: '24px 28px',
  background: '#ffffff',
  boxShadow: '0 4px 16px rgba(0,0,0,0.04)',
  marginTop: 24,
};

const TITLE_STYLE: React.CSSProperties = {
  fontSize: 16,
  fontWeight: 700,
  color: 'var(--text, #1d1d1f)',
  marginBottom: 16,
  letterSpacing: '-0.01em',
};

const TABLE_STYLE: React.CSSProperties = {
  width: '100%',
  borderCollapse: 'collapse',
  fontSize: 14,
};

const TH_STYLE: React.CSSProperties = {
  textAlign: 'left',
  padding: '10px 16px',
  borderBottom: '2px solid var(--line, #e5e5e7)',
  color: 'var(--muted, #86868b)',
  fontWeight: 600,
  fontSize: 12,
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  background: 'var(--bg1, #f8f9fa)',
};

const TD_STYLE: React.CSSProperties = {
  padding: '12px 16px',
  borderBottom: '1px solid var(--line, #e5e5e7)',
  color: 'var(--text, #1d1d1f)',
  fontVariantNumeric: 'tabular-nums',
};

function bestRowIndex(
  rows: PlaygroundBenchmarkRow[],
  sense: 'minimize' | 'maximize',
): number | null {
  let bestIdx: number | null = null;
  let bestVal: number | null = null;

  for (let i = 0; i < rows.length; i++) {
    const v = rows[i].best_feasible_objective;
    if (v == null || rows[i].status !== 'ran') continue;
    if (
      bestVal === null ||
      (sense === 'minimize' && v < bestVal) ||
      (sense === 'maximize' && v > bestVal)
    ) {
      bestVal = v;
      bestIdx = i;
    }
  }

  return bestIdx;
}

export function BenchmarkComparison({ rows, sense }: Props) {
  const highlightIdx = bestRowIndex(rows, sense);

  if (!rows || rows.length === 0) {
    return (
      <div style={WRAP_STYLE}>
        <div style={TITLE_STYLE}>求解器基准对比</div>
        <div style={{ color: 'var(--muted, #86868b)', fontSize: 14 }}>
          暂无 benchmark 数据
        </div>
      </div>
    );
  }

  return (
    <div style={WRAP_STYLE}>
      <div style={TITLE_STYLE}>求解器基准对比</div>

      <div style={{ overflowX: 'auto' }}>
        <table style={TABLE_STYLE}>
          <thead>
            <tr>
              <th style={TH_STYLE}>求解器</th>
              <th style={TH_STYLE}>状态</th>
              <th style={TH_STYLE}>最优可行目标</th>
              <th style={TH_STYLE}>可行样本比</th>
              <th style={TH_STYLE}>耗时 (ms)</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => {
              const isBest = i === highlightIdx;
              const rowBg = isBest
                ? 'rgba(212, 160, 23, 0.06)'
                : i % 2 === 0
                  ? 'transparent'
                  : 'rgba(0,0,0,0.02)';

              return (
                <tr key={row.solver} style={{ background: rowBg }}>
                  <td
                    style={{
                      ...TD_STYLE,
                      fontWeight: isBest ? 700 : 500,
                    }}
                  >
                    {row.solver}
                    {isBest && (
                      <span
                        style={{
                          marginLeft: 8,
                          fontSize: 10,
                          fontWeight: 700,
                          color: '#d4a017',
                          textTransform: 'uppercase',
                        }}
                      >
                        best
                      </span>
                    )}
                  </td>
                  <td style={TD_STYLE}>
                    <span
                      style={{
                        color: row.status === 'ran' ? '#059669' : 'var(--muted, #86868b)',
                        fontWeight: 600,
                        fontSize: 13,
                      }}
                    >
                      {row.status === 'ran' ? 'ran' : 'skipped'}
                    </span>
                  </td>
                  <td style={TD_STYLE}>
                    {row.best_feasible_objective != null
                      ? row.best_feasible_objective.toFixed(4)
                      : '—'}
                  </td>
                  <td style={TD_STYLE}>
                    {row.feasible_sample_ratio != null
                      ? `${(row.feasible_sample_ratio * 100).toFixed(1)}%`
                      : '—'}
                  </td>
                  <td style={TD_STYLE}>{row.total_ms.toFixed(1)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
