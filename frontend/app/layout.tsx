import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'idea-Ad | AI-Powered Ad Generation',
  description: 'Generate and deploy Facebook ads with a single prompt',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={inter.className}>
        <div className="min-h-screen">
          <header className="border-b border-slate-800/50 bg-slate-950/80 backdrop-blur-xl sticky top-0 z-50">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="flex justify-between items-center h-16">
                <a href="/" className="flex items-center gap-3 group">
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center shadow-lg shadow-primary-500/20 group-hover:shadow-primary-500/40 transition-shadow">
                    <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                  </div>
                  <span className="text-xl font-bold bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent">
                    idea-Ad
                  </span>
                </a>
                <nav className="flex items-center gap-1">
                  <a
                    href="/"
                    className="px-4 py-2 text-slate-400 hover:text-white hover:bg-slate-800/50 rounded-lg transition-all"
                  >
                    Create
                  </a>
                  <a
                    href="/history"
                    className="px-4 py-2 text-slate-400 hover:text-white hover:bg-slate-800/50 rounded-lg transition-all"
                  >
                    History
                  </a>
                </nav>
              </div>
            </div>
          </header>
          <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
