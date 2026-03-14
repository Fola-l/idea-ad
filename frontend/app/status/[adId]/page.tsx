'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import {
  Check,
  Clock,
  AlertCircle,
  ExternalLink,
  Copy,
  CheckCircle,
  Loader2,
  Home,
  Play,
  Pause,
  XCircle,
  RefreshCw,
  Zap,
} from 'lucide-react';
import { getAdStatus, activateAd, type StatusResponse, type ActivateResponse } from '@/lib/api';
import Link from 'next/link';


const META_AD_ACCOUNT_ID = process.env.NEXT_PUBLIC_META_AD_ACCOUNT_ID;
const META_BUSINESS_ID = process.env.NEXT_PUBLIC_META_BUSINESS_ID;
// Status categories for UX
type ReviewState = 'pending' | 'approved' | 'disapproved' | 'unknown';
type DeliveryState = 'paused' | 'active' | 'inactive';

function getReviewState(status: StatusResponse | null): ReviewState {
  if (!status?.effective_status) return 'unknown';

  if (status.effective_status === 'PENDING_REVIEW') {
    return 'pending';
  }
  if (status.effective_status === 'DISAPPROVED') {
    return 'disapproved';
  }
  // These statuses mean the ad passed review
  if (['ACTIVE', 'PAUSED', 'PREAPPROVED', 'CAMPAIGN_PAUSED', 'ADSET_PAUSED'].includes(status.effective_status)) {
    return 'approved';
  }
  return 'unknown';
}

function getDeliveryState(status: StatusResponse | null): DeliveryState {
  if (!status?.effective_status) return 'inactive';

  if (status.effective_status === 'ACTIVE') {
    return 'active';
  }
  if (['PAUSED', 'CAMPAIGN_PAUSED', 'ADSET_PAUSED', 'PREAPPROVED'].includes(status.effective_status)) {
    return 'paused';
  }
  return 'inactive';
}

function canActivate(status: StatusResponse | null): boolean {
  if (!status) return false;

  const reviewState = getReviewState(status);
  const deliveryState = getDeliveryState(status);

  // Can activate if approved and currently paused
  return reviewState === 'approved' && deliveryState === 'paused';
}

export default function StatusPage() {
  const params = useParams();
  const adId = params.adId as string;

  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [activating, setActivating] = useState(false);
  const [error, setError] = useState('');
  const [activateError, setActivateError] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);

  useEffect(() => {
    loadStatus();

    // Poll every 15 seconds while pending review
    const interval = setInterval(() => {
      if (getReviewState(status) === 'pending') {
        loadStatus();
      }
    }, 15000);
    return () => clearInterval(interval);
  }, [adId]);

  const loadStatus = async () => {
    try {
      const data = await getAdStatus(adId);
      setStatus(data);
      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load status');
    } finally {
      setLoading(false);
    }
  };

  const handleActivate = async () => {
    setActivating(true);
    setActivateError('');

    try {
      const result: ActivateResponse = await activateAd(adId);

      if (result.success) {
        // Refresh status to show new state
        await loadStatus();
      } else {
        setActivateError(result.error || 'Failed to activate ad');
      }
    } catch (err) {
      setActivateError(err instanceof Error ? err.message : 'Failed to activate ad');
    } finally {
      setActivating(false);
    }
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const reviewState = getReviewState(status);
  const deliveryState = getDeliveryState(status);
  const showActivateButton = canActivate(status);

  const adsManagerUrl =
    status?.campaign_id && status?.adset_id
      ? `https://adsmanager.facebook.com/adsmanager/manage/ads?act=${META_AD_ACCOUNT_ID}&business_id=${META_BUSINESS_ID}&nav_entry_point=mbs_sub_nav&selected_campaign_ids=${status.campaign_id}&selected_adset_ids=${status.adset_id}`
      : `https://adsmanager.facebook.com/adsmanager/manage/ads?act=${META_AD_ACCOUNT_ID}&business_id=${META_BUSINESS_ID}`;

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Main Status Card */}
      <div className="card">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-white">Ad Status</h1>
          <button
            onClick={loadStatus}
            className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
            title="Refresh status"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-3 mb-6 text-red-400 flex items-center gap-2">
            <AlertCircle className="w-5 h-5 shrink-0" />
            {error}
          </div>
        )}

        {/* Status Overview */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          {/* Review Status */}
          <div className={`p-4 rounded-xl border ${
            reviewState === 'approved'
              ? 'bg-green-500/10 border-green-500/30'
              : reviewState === 'disapproved'
              ? 'bg-red-500/10 border-red-500/30'
              : 'bg-yellow-500/10 border-yellow-500/30'
          }`}>
            <div className="flex items-center gap-2 mb-1">
              {reviewState === 'approved' ? (
                <CheckCircle className="w-5 h-5 text-green-400" />
              ) : reviewState === 'disapproved' ? (
                <XCircle className="w-5 h-5 text-red-400" />
              ) : (
                <Clock className="w-5 h-5 text-yellow-400" />
              )}
              <span className="text-sm font-medium text-slate-300">Review</span>
            </div>
            <p className={`text-lg font-semibold ${
              reviewState === 'approved'
                ? 'text-green-400'
                : reviewState === 'disapproved'
                ? 'text-red-400'
                : 'text-yellow-400'
            }`}>
              {reviewState === 'approved' ? 'Approved' : reviewState === 'disapproved' ? 'Disapproved' : 'Under Review'}
            </p>
          </div>

          {/* Delivery Status */}
          <div className={`p-4 rounded-xl border ${
            deliveryState === 'active'
              ? 'bg-green-500/10 border-green-500/30'
              : deliveryState === 'paused'
              ? 'bg-slate-500/10 border-slate-500/30'
              : 'bg-slate-800/50 border-slate-700/50'
          }`}>
            <div className="flex items-center gap-2 mb-1">
              {deliveryState === 'active' ? (
                <Play className="w-5 h-5 text-green-400" />
              ) : deliveryState === 'paused' ? (
                <Pause className="w-5 h-5 text-slate-400" />
              ) : (
                <XCircle className="w-5 h-5 text-slate-500" />
              )}
              <span className="text-sm font-medium text-slate-300">Delivery</span>
            </div>
            <p className={`text-lg font-semibold ${
              deliveryState === 'active'
                ? 'text-green-400'
                : deliveryState === 'paused'
                ? 'text-slate-400'
                : 'text-slate-500'
            }`}>
              {deliveryState === 'active' ? 'Running' : deliveryState === 'paused' ? 'Paused' : 'Inactive'}
            </p>
          </div>
        </div>

        {/* Disapproval Reason */}
        {reviewState === 'disapproved' && status?.ad_review_feedback && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 mb-6">
            <h3 className="text-sm font-semibold text-red-400 mb-2">Disapproval Reason</h3>
            <p className="text-sm text-slate-300">
              {typeof status.ad_review_feedback === 'object'
                ? JSON.stringify(status.ad_review_feedback, null, 2)
                : String(status.ad_review_feedback)}
            </p>
            <p className="text-xs text-slate-500 mt-2">
              Review Meta&apos;s advertising policies and edit your ad to comply.
            </p>
          </div>
        )}

        {/* Activation Section */}
        {showActivateButton && (
          <div className="bg-gradient-to-r from-primary-500/10 to-indigo-500/10 border border-primary-500/30 rounded-xl p-5 mb-6">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-primary-500/20 rounded-xl">
                <Zap className="w-6 h-6 text-primary-400" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-white mb-1">Ready to Go Live</h3>
                <p className="text-sm text-slate-400 mb-4">
                  Your ad has been approved by Meta. Activate it to start running and reaching your audience.
                </p>

                {activateError && (
                  <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-3 mb-4 text-red-400 text-sm flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 shrink-0" />
                    {activateError}
                  </div>
                )}

                <button
                  onClick={handleActivate}
                  disabled={activating}
                  className="btn-primary flex items-center gap-2"
                >
                  {activating ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Activating...
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4" />
                      Activate Ad
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Active Status */}
        {deliveryState === 'active' && (
          <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-5 mb-6">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-green-500/20 rounded-xl">
                <CheckCircle className="w-6 h-6 text-green-400" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-green-400 mb-1">Ad is Running</h3>
                <p className="text-sm text-slate-400">
                  Your ad is live and reaching your target audience. Monitor performance in Meta Ads Manager.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Pending Review Info */}
        {reviewState === 'pending' && (
          <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-5 mb-6">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-yellow-500/20 rounded-xl animate-pulse">
                <Clock className="w-6 h-6 text-yellow-400" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-yellow-400 mb-1">Under Review</h3>
                <p className="text-sm text-slate-400">
                  Meta is reviewing your ad. This usually takes 0-24 hours. We&apos;ll update this page automatically.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Ad Details */}
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-white">Details</h2>

          <div className="p-4 bg-slate-900/50 rounded-lg space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-slate-400 text-sm">Ad ID</span>
              <div className="flex items-center gap-2">
                <code className="text-slate-300 text-sm font-mono">{adId}</code>
                <button
                  className="text-slate-400 hover:text-white transition-colors"
                  onClick={() => copyToClipboard(adId, 'adId')}
                >
                  {copiedId === 'adId' ? (
                    <CheckCircle className="w-4 h-4 text-green-400" />
                  ) : (
                    <Copy className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-slate-400 text-sm">Effective Status</span>
              <span className="text-slate-300 text-sm font-mono">
                {status?.effective_status || 'Unknown'}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-slate-400 text-sm">Configured Status</span>
              <span className="text-slate-300 text-sm font-mono">
                {status?.configured_status || 'Unknown'}
              </span>
            </div>

            {status?.created_at && (
              <div className="flex items-center justify-between">
                <span className="text-slate-400 text-sm">Created</span>
                <span className="text-slate-300 text-sm">
                  {new Date(status.created_at).toLocaleString()}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Actions Card */}
      <div className="card">
        <h2 className="text-lg font-semibold text-white mb-4">Actions</h2>
        <div className="flex flex-col sm:flex-row gap-3">

          <a
            href={adsManagerUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-secondary flex items-center justify-center gap-2 flex-1"
          >
            <ExternalLink className="w-4 h-4" />
            View in Ads Manager
          </a>

          <Link
            href="/"
            className="btn-primary flex items-center justify-center gap-2 flex-1"
          >
            <Home className="w-4 h-4" />
            Create Another Ad
          </Link>
        </div>
      </div>
    </div>
  );
}
