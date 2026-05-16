import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: '发电机组组合 · 量子计算最优解',
  description: '任务管理与结果展示（演示）',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>
        <div className="shell">
          <header className="topbar">
            <div className="brand">
              <h1>量子计算最优解</h1>
              <small>Quantum Hackathon</small>
            </div>
            <nav className="nav">
              <a href="/scenarios/unit-commitment/tasks">任务管理</a>
            </nav>
          </header>
          {children}
        </div>
      </body>
    </html>
  );
}
