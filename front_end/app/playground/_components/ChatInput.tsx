import styles from '../playground.module.css';

type Props = {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  onStop: () => void;
  isStreaming: boolean;
  disabled?: boolean;
};

export function ChatInput({ value, onChange, onSubmit, isStreaming, disabled }: Props) {
  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!isStreaming && !disabled && value.trim()) onSubmit();
    }
  }

  return (
    <textarea
      className={styles.textarea}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      onKeyDown={handleKeyDown}
      readOnly={isStreaming}
      disabled={disabled}
      placeholder="请输入您的优化需求（例如：分析当前的量子计算资源分配，或者优化物流配送路径）"
    />
  );
}

