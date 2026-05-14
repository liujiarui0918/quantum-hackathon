import type { PlaygroundToolCallEvent, PlaygroundToolResultEvent } from '@/lib/playground-types';
import { SimulatedBadge } from '../SimulatedBadge';

type Props = {
  call: PlaygroundToolCallEvent;
  result: PlaygroundToolResultEvent | null;
};

export function ToolCallCard({ call, result }: Props) {
  return (
    <div style={{
      animation: 'fadeInUp 0.3s ease-out both',
      border: '1px solid var(--line)',
      borderRadius: '10px',
      padding: '14px 16px',
      background: '#ffffff',
      boxShadow: 'var(--shadow)',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', marginBottom: '8px' }}>
        <div>
          <span style={{ fontWeight: 700, fontSize: '14px', color: 'var(--accent2)', letterSpacing: '0.01em' }}>
            工具调用: {call.tool}
          </span>
          <div style={{ fontSize: '12px', color: 'var(--muted)', marginTop: '2px' }}>{call.summary}</div>
        </div>
        <SimulatedBadge />
      </div>

      {/* Input params */}
      <div style={{ marginTop: '8px' }}>
        <div style={{ fontSize: '10px', color: 'var(--muted)', letterSpacing: '0.06em', marginBottom: '4px', fontWeight: 600, textTransform: 'uppercase' }}>输入参数</div>
        <pre style={{
          margin: 0,
          padding: '10px 12px',
          borderRadius: '8px',
          background: 'var(--bg1)',
          border: '1px solid var(--line)',
          fontSize: '12px',
          fontFamily: "'SF Mono','Cascadia Code','Fira Code',monospace",
          color: 'var(--text)',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-all',
          maxHeight: '150px',
          overflowY: 'auto',
        }}>
          {JSON.stringify(call.input, null, 2)}
        </pre>
      </div>

      {/* Result */}
      {result && (
        <div style={{ marginTop: '8px' }}>
          <div style={{ fontSize: '10px', color: 'var(--muted)', letterSpacing: '0.06em', marginBottom: '4px', fontWeight: 600, textTransform: 'uppercase' }}>返回结果</div>
          <pre style={{
            margin: 0,
            padding: '10px 12px',
            borderRadius: '8px',
            background: 'var(--bg1)',
            border: '1px solid var(--line)',
            fontSize: '12px',
            fontFamily: "'SF Mono','Cascadia Code','Fira Code',monospace",
            color: 'var(--text)',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-all',
            maxHeight: '200px',
            overflowY: 'auto',
          }}>
            {JSON.stringify(result.output, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
