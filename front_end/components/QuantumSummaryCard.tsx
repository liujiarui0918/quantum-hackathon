'use client';

import type { BestSolutionDisplay } from '@/lib/map-quantum-to-business';

interface Props {
  bestSolution: BestSolutionDisplay;
  sense: 'minimize' | 'maximize';
}

const CARD_STYLE: React.CSSProperties = {
  border: '1px solid var(--line, #e5e5e7)',
  borderRadius: 16,
  padding: '24px 28px',
  background: '#ffffff',
  boxShadow: '0 4px 16px rgba(0,0,0,0.04)',
};

const TITLE_STYLE: React.CSSProperties = {
  fontSize: 16,
  fontWeight: 700,
  color: 'var(--text, #1d1d1f)',
  marginBottom: 20,
  letterSpacing: '-0.01em',
};

const GRID_STYLE: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
  gap: 14,
};

const ITEM_STYLE: React.CSSProperties = {
  padding: '14px 16px',
  borderRadius: 10,
  background: 'var(--bg1, #f8f9fa)',
  border: '1px solid var(--line, #e5e5e7)',
};

const LABEL_STYLE: React.CSSProperties = {
  fontSize: 12,
  fontWeight: 500,
  color: 'var(--muted, #86868b)',
  textTransform: 'uppercase',
  letterSpacing: '0.04em',
  marginBottom: 6,
};

const VALUE_STYLE: React.CSSProperties = {
  fontSize: 15,
  fontWeight: 600,
  color: 'var(--text, #1d1d1f)',
  fontVariantNumeric: 'tabular-nums',
};

const BITSTRING_STYLE: React.CSSProperties = {
  marginTop: 18,
  padding: '12px 16px',
  borderRadius: 8,
  background: '#1e1e1e',
  fontFamily: "'Fira Code', 'Cascadia Code', 'Consolas', monospace",
  fontSize: 13,
  color: '#e0e0e0',
  wordBreak: 'break-all',
  lineHeight: 1.7,
};

export function QuantumSummaryCard({ bestSolution, sense }: Props) {
  const { objective_value, is_feasible, bitstring, source_backend, total_violation } =
    bestSolution;

  const feasibleLabel = is_feasible === true ? '可行' : '不可行';
  const feasibleColor = is_feasible === true ? '#059669' : '#dc2626';
  const senseLabel = sense === 'minimize' ? 'min' : 'max';

  return (
    <div style={CARD_STYLE}>
      <div style={TITLE_STYLE}>量子求解结果</div>

      <div style={GRID_STYLE}>
        <div style={ITEM_STYLE}>
          <div style={LABEL_STYLE}>目标值 ({senseLabel})</div>
          <div style={VALUE_STYLE}>
            {objective_value != null ? objective_value.toFixed(4) : '—'}
          </div>
        </div>

        <div style={ITEM_STYLE}>
          <div style={LABEL_STYLE}>可行性</div>
          <div style={{ ...VALUE_STYLE, color: feasibleColor, fontWeight: 700 }}>
            {is_feasible === null ? '—' : feasibleLabel}
          </div>
        </div>

        <div style={ITEM_STYLE}>
          <div style={LABEL_STYLE}>来源后端</div>
          <div style={VALUE_STYLE}>{source_backend ?? '—'}</div>
        </div>

        {total_violation != null && total_violation > 0 && (
          <div style={ITEM_STYLE}>
            <div style={LABEL_STYLE}>违约总额</div>
            <div style={{ ...VALUE_STYLE, color: '#dc2626' }}>
              {total_violation.toFixed(4)}
            </div>
          </div>
        )}
      </div>

      {bitstring && (
        <div style={BITSTRING_STYLE}>
          <span style={{ color: '#888', marginRight: 8 }}>bitstring</span>
          {bitstring}
        </div>
      )}
    </div>
  );
}
