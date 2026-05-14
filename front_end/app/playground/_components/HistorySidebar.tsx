import type { PlaygroundHistoryItem } from '@/lib/playground-history';

type Props = {
  items: PlaygroundHistoryItem[];
  activeId?: string;
  onSelect?: (item: PlaygroundHistoryItem) => void;
};

export function HistorySidebar({ items, activeId, onSelect }: Props) {
  return (
    <div style={{
      padding: '14px',
      borderRadius: '12px',
      background: '#ffffff',
      border: '1px solid var(--line)',
      boxShadow: 'var(--shadow)',
      overflowY: 'auto',
      maxHeight: 'calc(100vh - 120px)',
    }}>
      <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--muted)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '12px' }}>
        最近会话
      </div>
      {items.length === 0 && (
        <div style={{ fontSize: '12px', color: 'var(--muted)' }}>暂无历史记录</div>
      )}
      {items.map((item) => (
        <div
          key={item.id}
          onClick={() => onSelect?.(item)}
          style={{
            padding: '8px 10px',
            marginBottom: '4px',
            borderRadius: '8px',
            border: activeId === item.id ? '1px solid var(--accent)' : '1px solid transparent',
            background: activeId === item.id ? 'var(--gold-soft)' : 'transparent',
            cursor: 'pointer',
            fontSize: '12px',
            transition: 'all 0.15s',
          }}
        >
          <div style={{ fontSize: '10px', color: 'var(--muted)', marginBottom: '2px' }}>{item.created_at.slice(0, 16)}</div>
          <div style={{ color: 'var(--text)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{item.prompt}</div>
        </div>
      ))}
    </div>
  );
}
