export function SimulatedBadge() {
  return (
    <span style={{
      fontSize: '10px',
      padding: '2px 8px',
      borderRadius: '6px',
      border: '1px solid rgba(232, 89, 12, 0.2)',
      color: 'var(--accent2)',
      background: 'var(--orange-soft)',
      fontWeight: 600,
      letterSpacing: '0.02em',
      whiteSpace: 'nowrap',
    }}>
      模拟调用
    </span>
  );
}
