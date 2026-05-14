import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: '平步青云量子求解平台',
  description: '任务管理与结果展示',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
      </head>
      <body>
        <div className="shell">
          <header className="topbar">
            <div className="brand">
              <h1>平步青云量子求解平台</h1>
              <small>Quantum Hackathon</small>
            </div>
            <nav className="nav">
              <a href="/scenarios/unit-commitment/tasks">发电机组</a>
              <a href="/playground">AI Playground</a>
            </nav>
          </header>
          {children}
        </div>
      </body>
    </html>
  );
}