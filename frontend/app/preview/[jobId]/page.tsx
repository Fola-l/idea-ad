'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  RefreshCw,
  Send,
  AlertCircle,
  X,
  Loader2,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import {
  getPreview,
  deployAd,
  regenerateImage,
  regenerateVoiceover,
  type PreviewResponse,
  type AdCopy,
  type Audience,
  type CampaignSettings,
} from '@/lib/api';

const CTA_OPTIONS = [
  { value: 'LEARN_MORE', label: 'Learn More' },
  { value: 'SHOP_NOW', label: 'Shop Now' },
  { value: 'SIGN_UP', label: 'Sign Up' },
  { value: 'GET_QUOTE', label: 'Get Quote' },
  { value: 'DOWNLOAD', label: 'Download' },
];

const OBJECTIVE_OPTIONS = [
  { value: 'OUTCOME_TRAFFIC', label: 'Traffic' },
  { value: 'OUTCOME_AWARENESS', label: 'Awareness' },
  { value: 'OUTCOME_LEADS', label: 'Leads' },
  { value: 'LINK_CLICKS', label: 'Link Clicks' },
  { value: 'LEAD_GENERATION', label: 'Lead Generation' },
];

// Minimum lifetime budget in NGN (₦108,300 = 10,830,000 kobo)
const MIN_LIFETIME_BUDGET_NGN = 108_300;
const CURRENCY_SYMBOL = '₦';
const CURRENCY_CODE = 'NGN';

export default function PreviewPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.jobId as string;

  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [deploying, setDeploying] = useState(false);
  const [regeneratingImage, setRegeneratingImage] = useState(false);
  const [regeneratingVoiceover, setRegeneratingVoiceover] = useState(false);
  const [sandboxMode, setSandboxMode] = useState(true);
  const [showDeployModal, setShowDeployModal] = useState(false);

  // Collapsible section state
  const [showAdCopy, setShowAdCopy] = useState(false);
  const [showAudience, setShowAudience] = useState(false);
  const [showCampaignSettings, setShowCampaignSettings] = useState(false);

  // Editable state
  const [adCopy, setAdCopy] = useState<AdCopy>({
    headline: '',
    body: '',
    cta: 'LEARN_MORE',
  });
  const [audience, setAudience] = useState<Audience | null>(null);
  const [campaignSettings, setCampaignSettings] = useState<CampaignSettings | null>(null);
  const [privacyPolicyUrl, setPrivacyPolicyUrl] = useState<string>('https://send247.uk/privacy-policy');

  useEffect(() => {
    loadPreview();
  }, [jobId]);

  const loadPreview = async () => {
    try {
      setLoading(true);
      const data = await getPreview(jobId);
      setPreview(data);

      if (data.ad_copy) {
        setAdCopy(data.ad_copy);
      }
      if (data.audience) {
        setAudience(data.audience);
      }
      if (data.campaign_settings) {
        setCampaignSettings(data.campaign_settings);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load preview');
    } finally {
      setLoading(false);
    }
  };

  const handleRegenerateImage = async () => {
    try {
      setRegeneratingImage(true);
      const result = await regenerateImage(jobId);
      setPreview((prev) =>
        prev
          ? {
              ...prev,
              creative_urls: {
                ...prev.creative_urls,
                image_url: result.image_url,
              },
            }
          : null
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to regenerate image');
    } finally {
      setRegeneratingImage(false);
    }
  };

  const handleRegenerateVoiceover = async () => {
    try {
      setRegeneratingVoiceover(true);
      const result = await regenerateVoiceover(jobId);
      setPreview((prev) =>
        prev
          ? {
              ...prev,
              creative_urls: {
                ...prev.creative_urls,
                voiceover_url: result.voiceover_url,
              },
            }
          : null
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to regenerate voiceover');
    } finally {
      setRegeneratingVoiceover(false);
    }
  };

  const handleDeploy = async () => {
    if (!audience || !campaignSettings) return;

    // Validate privacy policy URL for lead generation campaigns
    if (campaignSettings.objective === 'LEAD_GENERATION' && !privacyPolicyUrl) {
      setError('Privacy Policy URL is required for Lead Generation campaigns');
      return;
    }

    try {
      setDeploying(true);
      const result = await deployAd({
        job_id: jobId,
        approved_copy: adCopy,
        approved_audience: audience,
        approved_settings: campaignSettings,
        privacy_policy_url: privacyPolicyUrl,
        sandbox_mode: sandboxMode,
      });

      if (result.ad_id) {
        router.push(`/status/${result.ad_id}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to deploy ad');
      setDeploying(false);
    }
  };

  const removeInterest = (index: number) => {
    if (!audience) return;
    const newInterests = [...audience.interests];
    newInterests.splice(index, 1);
    setAudience({ ...audience, interests: newInterests });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="card bg-red-500/10 border-red-500/50">
          <div className="flex items-center gap-3 text-red-400">
            <AlertCircle className="w-6 h-6" />
            <div>
              <h3 className="font-medium">Error</h3>
              <p className="text-sm">{error}</p>
            </div>
          </div>
          <button
            className="btn-secondary mt-4"
            onClick={() => {
              setError('');
              loadPreview();
            }}
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  if (!preview) return null;

  const hasVideo = preview.creative_urls?.video_url;
  const hasImage = preview.creative_urls?.image_url;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Preview & Edit</h1>
          <p className="text-slate-400 text-sm mt-1">Review your ad before deploying to Meta</p>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <span className="px-3 py-1 rounded-full bg-primary-500/10 border border-primary-500/30 text-primary-400">
            {preview.format === 'video' ? 'Video Ad' : 'Image Ad'}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column - Creative Preview */}
        <div className="lg:sticky lg:top-24 lg:self-start">
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-white">Creative Preview</h2>
            </div>

            {/* Video/Image Preview */}
            <div className="aspect-square bg-slate-950 rounded-xl overflow-hidden mb-4 relative ring-1 ring-slate-800">
              {hasVideo ? (
                <video
                  src={preview.creative_urls?.video_url}
                  className="w-full h-full object-cover"
                  controls
                />
              ) : hasImage ? (
                <img
                  src={preview.creative_urls?.image_url}
                  alt="Ad creative"
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="flex items-center justify-center h-full text-slate-500">
                  No creative available
                </div>
              )}
            </div>

            {/* Regenerate Buttons */}
            <div className="flex gap-3">
              {hasImage && (
                <button
                  className="btn-secondary flex items-center justify-center gap-2 flex-1 text-sm"
                  onClick={handleRegenerateImage}
                  disabled={regeneratingImage}
                >
                  {regeneratingImage ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <RefreshCw className="w-4 h-4" />
                  )}
                  New Image
                </button>
              )}
              {hasVideo && preview.voiceover_script && (
                <button
                  className="btn-secondary flex items-center justify-center gap-2 flex-1 text-sm"
                  onClick={handleRegenerateVoiceover}
                  disabled={regeneratingVoiceover}
                >
                  {regeneratingVoiceover ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <RefreshCw className="w-4 h-4" />
                  )}
                  New Voiceover
                </button>
              )}
            </div>

            {/* Creative Brief */}
            {preview.creative_brief && (
              <div className="mt-4 p-4 bg-slate-950/50 rounded-xl border border-slate-800">
                <h3 className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">Creative Brief</h3>
                <p className="text-sm text-slate-300 leading-relaxed">{preview.creative_brief}</p>
              </div>
            )}
          </div>
        </div>

        {/* Right Column - Settings */}
        <div className="space-y-5">
        {/* Ad Copy */}
        <div className="card">
          <button
            type="button"
            className="flex items-center justify-between w-full mb-5 group"
            onClick={() => setShowAdCopy(!showAdCopy)}
          >
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center">
                <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
              </div>
              <h2 className="text-lg font-semibold text-white">Ad Copy</h2>
              {!showAdCopy && (
                <span className="text-xs text-slate-500">
                  • Headline • Body • CTA
                </span>
              )}
            </div>
            {showAdCopy ? (
              <ChevronUp className="w-5 h-5 text-slate-400 group-hover:text-slate-300 transition-colors" />
            ) : (
              <ChevronDown className="w-5 h-5 text-slate-400 group-hover:text-slate-300 transition-colors" />
            )}
          </button>

          {showAdCopy && (
            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-slate-300">Headline</label>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${adCopy.headline.length >= 35 ? 'bg-yellow-500/20 text-yellow-400' : 'bg-slate-800 text-slate-500'}`}>
                    {adCopy.headline.length}/40
                  </span>
                </div>
                <input
                  type="text"
                  className="input"
                  value={adCopy.headline}
                  onChange={(e) =>
                    setAdCopy({ ...adCopy, headline: e.target.value.slice(0, 40) })
                  }
                  maxLength={40}
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-slate-300">Body</label>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${adCopy.body.length >= 110 ? 'bg-yellow-500/20 text-yellow-400' : 'bg-slate-800 text-slate-500'}`}>
                    {adCopy.body.length}/125
                  </span>
                </div>
                <textarea
                  className="textarea h-24"
                  value={adCopy.body}
                  onChange={(e) =>
                    setAdCopy({ ...adCopy, body: e.target.value.slice(0, 125) })
                  }
                  maxLength={125}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Call to Action
                </label>
                <select
                  className="input"
                  value={adCopy.cta}
                  onChange={(e) => setAdCopy({ ...adCopy, cta: e.target.value })}
                >
                  {CTA_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}
        </div>

        {/* Audience */}
        {audience && (
          <div className="card">
            <button
              type="button"
              className="flex items-center justify-between w-full mb-4 group"
              onClick={() => setShowAudience(!showAudience)}
            >
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-semibold text-white">Audience</h2>
                {!showAudience && (
                  <span className="text-xs text-slate-500">
                    • Ages {audience.core_audience.age_min}-{audience.core_audience.age_max} • {audience.interests.length} interests
                  </span>
                )}
              </div>
              {showAudience ? (
                <ChevronUp className="w-5 h-5 text-slate-400 group-hover:text-slate-300 transition-colors" />
              ) : (
                <ChevronDown className="w-5 h-5 text-slate-400 group-hover:text-slate-300 transition-colors" />
              )}
            </button>

            {showAudience && (
              <div className="space-y-4">
              {/* Age Range */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">
                    Age Min
                  </label>
                  <input
                    type="number"
                    className="input"
                    value={audience.core_audience.age_min}
                    onChange={(e) =>
                      setAudience({
                        ...audience,
                        core_audience: {
                          ...audience.core_audience,
                          age_min: parseInt(e.target.value) || 18,
                        },
                      })
                    }
                    min={18}
                    max={65}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">
                    Age Max
                  </label>
                  <input
                    type="number"
                    className="input"
                    value={audience.core_audience.age_max}
                    onChange={(e) =>
                      setAudience({
                        ...audience,
                        core_audience: {
                          ...audience.core_audience,
                          age_max: parseInt(e.target.value) || 65,
                        },
                      })
                    }
                    min={18}
                    max={65}
                  />
                </div>
              </div>

              {/* Interests */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Interests
                </label>
                <div className="flex flex-wrap gap-2">
                  {audience.interests.map((interest, index) => (
                    <span key={index} className="chip">
                      {interest.name}
                      <button
                        className="chip-remove"
                        onClick={() => removeInterest(index)}
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  ))}
                </div>
              </div>

              {/* Rationale */}
              <div className="p-3 bg-slate-900/50 rounded-lg">
                <h3 className="text-sm font-medium text-slate-400 mb-1">
                  Targeting Rationale
                </h3>
                <p className="text-sm text-slate-300">
                  {audience.audience_rationale}
                </p>
              </div>
            </div>
            )}
          </div>
        )}

        {/* Campaign Settings */}
        {campaignSettings && (() => {
          const lifetimeBudget = campaignSettings.daily_budget * campaignSettings.duration_days;
          const isBudgetValid = lifetimeBudget >= MIN_LIFETIME_BUDGET_NGN;
          const budgetShortfall = MIN_LIFETIME_BUDGET_NGN - lifetimeBudget;
          const suggestedDaily = Math.ceil(MIN_LIFETIME_BUDGET_NGN / campaignSettings.duration_days);

          return (
            <div className="card">
              <button
                type="button"
                className="flex items-center justify-between w-full mb-4 group"
                onClick={() => setShowCampaignSettings(!showCampaignSettings)}
              >
                <div className="flex items-center gap-2">
                  <h2 className="text-lg font-semibold text-white">Campaign Settings</h2>
                  {!showCampaignSettings && (
                    <span className="text-xs text-slate-500">
                      • {CURRENCY_SYMBOL}{lifetimeBudget.toLocaleString()} • {campaignSettings.duration_days} days
                    </span>
                  )}
                </div>
                {showCampaignSettings ? (
                  <ChevronUp className="w-5 h-5 text-slate-400 group-hover:text-slate-300 transition-colors" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-slate-400 group-hover:text-slate-300 transition-colors" />
                )}
              </button>

              {showCampaignSettings && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">
                      Objective
                    </label>
                  <select
                    className="input"
                    value={campaignSettings.objective}
                    onChange={(e) =>
                      setCampaignSettings({
                        ...campaignSettings,
                        objective: e.target.value,
                      })
                    }
                  >
                    {OBJECTIVE_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                    </select>
                  </div>

                  {/* Budget Section */}
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-slate-300 mb-1">
                          Daily Budget ({CURRENCY_CODE})
                        </label>
                        <div className="relative">
                          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 font-medium">
                            {CURRENCY_SYMBOL}
                          </span>
                          <input
                            type="number"
                            className="input-currency pl-8"
                            value={campaignSettings.daily_budget}
                            onChange={(e) =>
                              setCampaignSettings({
                                ...campaignSettings,
                                daily_budget: parseFloat(e.target.value) || 0,
                              })
                            }
                            min={1}
                            step={1000}
                            placeholder="e.g. 25000"
                          />
                        </div>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-slate-300 mb-1">
                          Duration
                        </label>
                        <div className="relative">
                          <input
                            type="number"
                            className="input pr-14"
                            value={campaignSettings.duration_days}
                            onChange={(e) =>
                              setCampaignSettings({
                                ...campaignSettings,
                                duration_days: parseInt(e.target.value) || 1,
                              })
                            }
                            min={1}
                            max={30}
                          />
                          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm">
                            days
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Budget Summary */}
                    <div className="budget-summary">
                      <div className="flex justify-between items-center">
                        <span className="text-slate-400 text-sm">Lifetime Budget</span>
                        <span className={`text-lg font-semibold ${isBudgetValid ? 'text-white' : 'text-red-400'}`}>
                          {CURRENCY_SYMBOL}{lifetimeBudget.toLocaleString()}
                        </span>
                      </div>
                      <div className="flex justify-between items-center mt-1">
                        <span className="text-slate-500 text-xs">Minimum required</span>
                        <span className="text-slate-500 text-xs">
                          {CURRENCY_SYMBOL}{MIN_LIFETIME_BUDGET_NGN.toLocaleString()}
                        </span>
                      </div>
                    </div>

                    {/* Budget Validation Message */}
                    {!isBudgetValid && (
                      <div className="budget-error">
                        <p className="font-medium">Budget too low</p>
                        <p className="mt-1">
                          You need {CURRENCY_SYMBOL}{budgetShortfall.toLocaleString()} more.
                          Try setting daily budget to {CURRENCY_SYMBOL}{suggestedDaily.toLocaleString()} or increase duration.
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Lead Generation - Privacy Policy URL */}
                  {campaignSettings.objective === 'LEAD_GENERATION' && (
                    <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4">
                      <div className="flex items-start gap-2 mb-3">
                        <svg className="w-5 h-5 text-amber-400 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                        <div>
                          <h4 className="text-sm font-medium text-amber-400">Lead Generation Campaign</h4>
                          <p className="text-xs text-amber-300/80 mt-1">
                            Meta requires a privacy policy URL to collect leads via Facebook forms.
                          </p>
                        </div>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-slate-300 mb-1">
                          Privacy Policy URL *
                        </label>
                        <input
                          type="url"
                          className="input"
                          value={privacyPolicyUrl}
                          onChange={(e) => setPrivacyPolicyUrl(e.target.value)}
                          placeholder="https://send247.uk/privacy-policy"
                          required
                        />
                      </div>
                    </div>
                  )}

                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">
                      Destination URL
                    </label>
                    <input
                      type="url"
                      className="input"
                      value={campaignSettings.destination_url}
                      onChange={(e) =>
                        setCampaignSettings({
                          ...campaignSettings,
                          destination_url: e.target.value,
                        })
                      }
                      placeholder="https://yourproduct.com"
                    />
                  </div>
                </div>
              )}
            </div>
          );
        })()}

        {/* Deploy Section */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white">Deploy</h2>
            <label className="flex items-center gap-2 cursor-pointer">
              <span className="text-sm text-slate-400">
                {sandboxMode ? 'Sandbox' : 'Live'}
              </span>
              <div
                className={`relative w-12 h-6 rounded-full transition-colors ${
                  sandboxMode ? 'bg-slate-600' : 'bg-green-600'
                }`}
                onClick={() => setSandboxMode(!sandboxMode)}
              >
                <div
                  className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${
                    sandboxMode ? 'left-1' : 'left-7'
                  }`}
                />
              </div>
            </label>
          </div>

          {!sandboxMode && (
            <div className="bg-yellow-500/10 border border-yellow-500/50 rounded-lg p-3 mb-4 text-yellow-400 text-sm">
              <strong>Warning:</strong> Live mode will use real ad spend. Make sure
              your Meta account has billing set up.
            </div>
          )}

          {(() => {
            const lifetimeBudget = (campaignSettings?.daily_budget || 0) * (campaignSettings?.duration_days || 0);
            const isBudgetValid = lifetimeBudget >= MIN_LIFETIME_BUDGET_NGN;
            const canDeploy = campaignSettings?.destination_url && isBudgetValid;

            return (
              <>
                <button
                  className="btn-primary w-full flex items-center justify-center gap-2"
                  onClick={() => setShowDeployModal(true)}
                  disabled={deploying || !canDeploy}
                >
                  {deploying ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <Send className="w-5 h-5" />
                  )}
                  Deploy to Facebook
                </button>

                {!campaignSettings?.destination_url && (
                  <p className="text-xs text-red-400 mt-2">
                    Please enter a destination URL before deploying
                  </p>
                )}

                {campaignSettings?.destination_url && !isBudgetValid && (
                  <p className="text-xs text-red-400 mt-2">
                    Lifetime budget must be at least {CURRENCY_SYMBOL}{MIN_LIFETIME_BUDGET_NGN.toLocaleString()}
                  </p>
                )}
              </>
            );
          })()}
        </div>
        </div>
      </div>

      {/* Deploy Confirmation Modal */}
      {showDeployModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="card max-w-md w-full">
            <h3 className="text-xl font-semibold text-white mb-4">
              Confirm Deployment
            </h3>
            <div className="space-y-4 mb-6">
              {/* Mode */}
              <div className="flex justify-between items-center py-2 border-b border-slate-700">
                <span className="text-slate-400">Mode</span>
                <span className={`font-medium ${sandboxMode ? 'text-slate-300' : 'text-green-400'}`}>
                  {sandboxMode ? 'Sandbox (Test)' : 'Live'}
                </span>
              </div>

              {/* Daily Budget */}
              <div className="flex justify-between items-center py-2 border-b border-slate-700">
                <span className="text-slate-400">Daily Budget</span>
                <span className="text-white font-medium">
                  {CURRENCY_SYMBOL}{(campaignSettings?.daily_budget || 0).toLocaleString()} / day
                </span>
              </div>

              {/* Duration */}
              <div className="flex justify-between items-center py-2 border-b border-slate-700">
                <span className="text-slate-400">Duration</span>
                <span className="text-white font-medium">
                  {campaignSettings?.duration_days} days
                </span>
              </div>

              {/* Total Budget */}
              <div className="flex justify-between items-center py-3 bg-slate-900/50 rounded-lg px-3 -mx-3">
                <span className="text-slate-300 font-medium">Lifetime Budget</span>
                <span className="text-xl font-bold text-primary-400">
                  {CURRENCY_SYMBOL}{(
                    (campaignSettings?.daily_budget || 0) *
                    (campaignSettings?.duration_days || 0)
                  ).toLocaleString()}
                </span>
              </div>

              <p className="text-slate-400 text-sm">
                Ad will be created as <strong className="text-slate-300">PAUSED</strong>.
                Activate it in Meta Ads Manager when ready.
              </p>
            </div>
            <div className="flex gap-3">
              <button
                className="btn-secondary flex-1"
                onClick={() => setShowDeployModal(false)}
              >
                Cancel
              </button>
              <button
                className="btn-primary flex-1"
                onClick={() => {
                  setShowDeployModal(false);
                  handleDeploy();
                }}
              >
                Deploy
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
