'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Clock,
  CheckCircle,
  AlertCircle,
  Loader2,
  ExternalLink,
  ChevronRight,
} from 'lucide-react';
import { getHistory, type AdRun } from '@/lib/api';

const STATUS_CONFIG = {
  pending: { icon: Clock, color: 'text-slate-400', bg: 'bg-slate-500/20' },
  generating: { icon: Loader2, color: 'text-blue-400', bg: 'bg-blue-500/20' },
  preview: { icon: Clock, color: 'text-yellow-400', bg: 'bg-yellow-500/20' },
  deploying: { icon: Loader2, color: 'text-blue-400', bg: 'bg-blue-500/20' },
  live: { icon: CheckCircle, color: 'text-green-400', bg: 'bg-green-500/20' },
  failed: { icon: AlertCircle, color: 'text-red-400', bg: 'bg-red-500/20' },
};

export default function HistoryPage() {
  const [runs, setRuns] = useState<AdRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      const data = await getHistory();
      setRuns(data.runs);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load history');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-white">Ad History</h1>
        <Link href="/" className="btn-primary">
          Create New Ad
        </Link>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-4 mb-6 text-red-400">
          {error}
        </div>
      )}

      {runs.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-slate-400 mb-4">No ad runs yet</p>
          <Link href="/" className="btn-primary">
            Create Your First Ad
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {runs.map((run) => {
            const statusConfig =
              STATUS_CONFIG[run.status as keyof typeof STATUS_CONFIG] ||
              STATUS_CONFIG.pending;
            const StatusIcon = statusConfig.icon;

            return (
              <div key={run.id} className="card hover:bg-slate-800/70 transition-colors">
                <div className="flex items-start gap-4">
                  {/* Status Icon */}
                  <div
                    className={`w-10 h-10 rounded-full flex items-center justify-center ${statusConfig.bg}`}
                  >
                    <StatusIcon
                      className={`w-5 h-5 ${statusConfig.color} ${
                        run.status === 'generating' || run.status === 'deploying'
                          ? 'animate-spin'
                          : ''
                      }`}
                    />
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className={`text-xs font-medium px-2 py-0.5 rounded-full ${statusConfig.bg} ${statusConfig.color}`}
                      >
                        {run.status}
                      </span>
                      {run.sandbox_mode && (
                        <span className="text-xs text-slate-500">Sandbox</span>
                      )}
                    </div>

                    <p className="text-white font-medium truncate mb-1">
                      {run.ad_copy?.headline || 'Untitled Ad'}
                    </p>

                    <p className="text-sm text-slate-400 line-clamp-2 mb-2">
                      {run.prompt}
                    </p>

                    <div className="flex items-center gap-4 text-xs text-slate-500">
                      <span>
                        {new Date(run.created_at).toLocaleDateString('en-GB', {
                          day: 'numeric',
                          month: 'short',
                          year: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                      {run.campaign_settings && (
                        <span>
                          {run.campaign_settings.daily_budget}/day •{' '}
                          {run.campaign_settings.duration_days} days
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2">
                    {run.status === 'preview' && (
                      <Link
                        href={`/preview/${run.job_id}`}
                        className="btn-secondary text-sm py-1.5 px-3"
                      >
                        Continue
                      </Link>
                    )}
                    {run.status === 'live' && run.meta_ids?.ad_id && (
                      <Link
                        href={`/status/${run.meta_ids.ad_id}`}
                        className="btn-secondary text-sm py-1.5 px-3 flex items-center gap-1"
                      >
                        View Status
                        <ChevronRight className="w-4 h-4" />
                      </Link>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
