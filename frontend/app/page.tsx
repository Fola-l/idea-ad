'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Sparkles, ChevronDown, ChevronUp, Loader2, Zap, Target, TrendingUp, Settings } from 'lucide-react';
import { generateAd, generateCreative } from '@/lib/api';

const LOADING_MESSAGES = [
  'Analyzing your prompt...',
  'Generating ad strategy...',
  'Crafting audience targeting...',
  'Creating voiceover script...',
  'Generating creative assets...',
  'Assembling your ad...',
  'Almost ready...',
];

const FEATURES = [
  { icon: Zap, title: 'AI-Powered', desc: 'Claude generates strategy' },
  { icon: Target, title: 'Smart Targeting', desc: 'Auto audience discovery' },
  { icon: TrendingUp, title: 'One-Click Deploy', desc: 'Direct to Meta Ads' },
];

const OBJECTIVE_OPTIONS = [
  { value: 'OUTCOME_TRAFFIC', label: 'Traffic' },
  { value: 'OUTCOME_AWARENESS', label: 'Awareness' },
  { value: 'OUTCOME_LEADS', label: 'Leads' },
  { value: 'LINK_CLICKS', label: 'Link Clicks' },
];

// Minimum lifetime budget in NGN (₦108,300 = 10,830,000 kobo)
const MIN_LIFETIME_BUDGET_NGN = 108_300;
const CURRENCY_SYMBOL = '₦';
const CURRENCY_CODE = 'NGN';

export default function Home() {
  const router = useRouter();
  const [prompt, setPrompt] = useState('');
  const [showExamples, setShowExamples] = useState(false);
  const [showCampaignSettings, setShowCampaignSettings] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('');
  const [error, setError] = useState('');

  // Campaign settings (optional overrides)
  const [dailyBudget, setDailyBudget] = useState<number>(25000);
  const [duration, setDuration] = useState<number>(5);
  const [objective, setObjective] = useState<string>('OUTCOME_TRAFFIC');
  const [destinationUrl, setDestinationUrl] = useState<string>('https://send247.uk/');

  const handleGenerate = async () => {
    if (!prompt.trim()) {
      setError('Please enter a prompt');
      return;
    }

    setLoading(true);
    setError('');

    // Cycle through loading messages
    let messageIndex = 0;
    const messageInterval = setInterval(() => {
      setLoadingMessage(LOADING_MESSAGES[messageIndex]);
      messageIndex = (messageIndex + 1) % LOADING_MESSAGES.length;
    }, 3000);

    setLoadingMessage(LOADING_MESSAGES[0]);

    try {
      // Step 1: Generate ad strategy
      const response = await generateAd({
        prompt,
        destination_url: destinationUrl,
      });

      // Step 2: Generate creative assets
      setLoadingMessage('Generating creative assets...');
      await generateCreative(response.job_id);

      clearInterval(messageInterval);

      // Redirect to preview
      router.push(`/preview/${response.job_id}`);
    } catch (err) {
      clearInterval(messageInterval);
      setError(err instanceof Error ? err.message : 'Something went wrong');
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto">
      {/* Hero Section */}
      <div className="text-center mb-10">
        <h1 className="text-4xl sm:text-5xl font-bold text-white mb-4 tracking-tight">
          Send247 Ad Studio
        </h1>

        {/* Feature Pills */}
        <div className="flex flex-wrap justify-center gap-3 mt-6">
          {FEATURES.map((feature, i) => (
            <div key={i} className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800/50 border border-slate-700/50 text-sm">
              <feature.icon className="w-4 h-4 text-primary-400" />
              <span className="text-slate-300">{feature.title}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="card glow-border">
        {/* Main Prompt */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-slate-300 mb-2">
            What do you want to advertise?
          </label>
          <textarea
            className="textarea h-32"
            placeholder="e.g., Promote Send247 to pharmacies in Stratford. Focus on fast, reliable delivery. Professional tone. £100/day for 5 days."
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            disabled={loading}
          />
          <p className="text-xs text-slate-500 mt-1">
            Include: campaign idea, target audience, tone, budget (optional)
          </p>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-3 mb-6 text-red-400">
            {error}
          </div>
        )}

        {/* Campaign Settings (Optional) */}
        <div className="mb-6 border-t border-slate-700/50 pt-6">
          <button
            type="button"
            className="flex items-center justify-between w-full mb-4 group"
            onClick={() => setShowCampaignSettings(!showCampaignSettings)}
          >
            <div className="flex items-center gap-2">
              <Settings className="w-5 h-5 text-slate-400 group-hover:text-slate-300 transition-colors" />
              <h3 className="text-sm font-medium text-slate-300 group-hover:text-white transition-colors">
                Campaign Settings
              </h3>
              <span className="text-xs text-slate-500">(Optional - AI will set defaults)</span>
            </div>
            {showCampaignSettings ? (
              <ChevronUp className="w-4 h-4 text-slate-400 group-hover:text-slate-300 transition-colors" />
            ) : (
              <ChevronDown className="w-4 h-4 text-slate-400 group-hover:text-slate-300 transition-colors" />
            )}
          </button>

          {showCampaignSettings && (
            <div className="space-y-4 animate-in fade-in slide-in-from-top-2 duration-200">
              {/* Budget & Duration */}
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
                      className="input pl-8"
                      value={dailyBudget}
                      onChange={(e) => setDailyBudget(parseFloat(e.target.value) || 0)}
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
                      value={duration}
                      onChange={(e) => setDuration(parseInt(e.target.value) || 1)}
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
              <div className="bg-slate-800/50 rounded-lg p-3">
                <div className="flex justify-between items-center">
                  <span className="text-slate-400 text-sm">Lifetime Budget</span>
                  <span className={`text-lg font-semibold ${(dailyBudget * duration) >= MIN_LIFETIME_BUDGET_NGN ? 'text-white' : 'text-red-400'}`}>
                    {CURRENCY_SYMBOL}{(dailyBudget * duration).toLocaleString()}
                  </span>
                </div>
                <div className="flex justify-between items-center mt-1">
                  <span className="text-slate-500 text-xs">Minimum required</span>
                  <span className="text-slate-500 text-xs">
                    {CURRENCY_SYMBOL}{MIN_LIFETIME_BUDGET_NGN.toLocaleString()}
                  </span>
                </div>
              </div>

              {/* Objective */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  Objective
                </label>
                <select
                  className="input"
                  value={objective}
                  onChange={(e) => setObjective(e.target.value)}
                >
                  {OBJECTIVE_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Destination URL */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  Destination URL
                </label>
                <input
                  type="url"
                  className="input"
                  value={destinationUrl}
                  onChange={(e) => setDestinationUrl(e.target.value)}
                  placeholder="https://send247.uk/"
                />
              </div>
            </div>
          )}
        </div>

        {/* Generate Button */}
        <button
          className="btn-primary w-full flex items-center justify-center gap-2 py-4 text-lg font-semibold"
          onClick={handleGenerate}
          disabled={loading}
        >
          {loading ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              {loadingMessage}
            </>
          ) : (
            <>
              <Sparkles className="w-5 h-5" />
              Generate Ad
            </>
          )}
        </button>
      </div>

      {/* Example Prompts */}
      <div className="mt-10">
        <button
          type="button"
          className="flex items-center justify-center gap-2 w-full py-3 text-slate-400 hover:text-slate-300 transition-colors group"
          onClick={() => setShowExamples(!showExamples)}
        >
          <div className="h-px flex-1 bg-gradient-to-r from-transparent via-slate-700 to-transparent group-hover:via-slate-600 transition-colors" />
          <span className="text-sm font-medium flex items-center gap-2">
            {showExamples ? 'Try an example' : 'See examples'}
            {showExamples ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </span>
          <div className="h-px flex-1 bg-gradient-to-r from-transparent via-slate-700 to-transparent group-hover:via-slate-600 transition-colors" />
        </button>

        {showExamples && (
          <div className="grid gap-3 mt-4 animate-in fade-in slide-in-from-top-2 duration-200">
            {[
              { text: 'Target pharmacies in Stratford needing faster prescription deliveries. Focus on reliability and speed. Professional tone. £50/day for 5 days.', tag: 'Pharmacies' },
              { text: 'Reach e-commerce businesses in London struggling with same-day delivery. Emphasize API integration and tech. Modern tone. £75/day for 4 days.', tag: 'E-commerce' },
              { text: 'Advertise to retail shops in Manchester needing urgent courier services. Highlight 24/7 availability. Friendly tone. £60/day for 5 days.', tag: 'Retail' },
            ].map((example, index) => (
              <button
                key={index}
                className="group w-full text-left p-4 rounded-xl bg-slate-900/50 hover:bg-slate-800/70 border border-slate-800 hover:border-slate-700 text-slate-300 text-sm transition-all"
                onClick={() => setPrompt(example.text)}
                disabled={loading}
              >
                <div className="flex items-start gap-3">
                  <span className="shrink-0 px-2 py-1 rounded-md bg-slate-800 text-xs font-medium text-slate-400 group-hover:bg-primary-500/20 group-hover:text-primary-400 transition-colors">
                    {example.tag}
                  </span>
                  <span className="text-slate-400 group-hover:text-slate-300 transition-colors">
                    {example.text}
                  </span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
