export function Banner() {
  return (
    <div style={{
      gridColumn: '1 / -1',
      padding: '10px 16px',
      borderRadius: '10px',
      border: '1px solid rgba(232, 89, 12, 0.2)',
      background: 'rgba(232, 89, 12, 0.04)',
      color: 'var(--accent2)',
      fontSize: '12px',
      fontWeight: 500,
      letterSpacing: '0.02em',
      textAlign: 'center',
      boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
    }}>
      演示模式 · 所有 AI 思考过程与工具调用均为本地模拟数据
    </div>
  );
}
