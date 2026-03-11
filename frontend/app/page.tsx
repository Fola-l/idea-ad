'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Sparkles, Upload, ChevronDown, ChevronUp, Loader2, Zap, Target, TrendingUp } from 'lucide-react';
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

export default function Home() {
  const router = useRouter();
  const [prompt, setPrompt] = useState('');
  const [destinationUrl, setDestinationUrl] = useState('');
  const [showAssets, setShowAssets] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('');
  const [error, setError] = useState('');

  // Brand assets state
  const [logoUrl, setLogoUrl] = useState('');
  const [demoImageUrl, setDemoImageUrl] = useState('');
  const [demoVideoUrl, setDemoVideoUrl] = useState('');
  const [brandColors, setBrandColors] = useState<string[]>(['#0ea5e9']);

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
        destination_url: destinationUrl || undefined,
        logo_url: logoUrl || undefined,
        demo_image_url: demoImageUrl || undefined,
        demo_video_url: demoVideoUrl || undefined,
        brand_colors: brandColors.length > 0 ? brandColors : undefined,
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
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary-500/10 border border-primary-500/20 text-primary-400 text-sm mb-6">
          <Sparkles className="w-4 h-4" />
          <span>Powered by Claude AI</span>
        </div>
        <h1 className="text-4xl sm:text-5xl font-bold text-white mb-4 tracking-tight">
          Create Ads with
          <span className="bg-gradient-to-r from-primary-400 to-indigo-400 bg-clip-text text-transparent"> AI</span>
        </h1>
        <p className="text-slate-400 text-lg max-w-xl mx-auto">
          Describe your product and audience. We generate the ad copy, creative, targeting, and deploy to Meta.
        </p>

        {/* Feature Pills */}
        <div className="flex flex-wrap justify-center gap-3 mt-6">
          {FEATURES.map((feature, i) => (
            <div key={i} className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800/50 border border-slate-700/50 text-sm">
              <feature.icon className="w-4 h-4 text-primary-400" />
              <span className="text-slate-300">{feature.title}</span>
              <span className="text-slate-500">·</span>
              <span className="text-slate-500">{feature.desc}</span>
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
            placeholder="e.g., Promote the parcel delivery API to logistics managers. Focus on the MCP integration. Energetic tone. 5000/day for 5 days."
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            disabled={loading}
          />
          <p className="text-xs text-slate-500 mt-1">
            Include: product, target audience, tone, budget (optional)
          </p>
        </div>

        {/* Destination URL */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Landing Page URL
          </label>
          <input
            type="url"
            className="input"
            placeholder="https://yourproduct.com"
            value={destinationUrl}
            onChange={(e) => setDestinationUrl(e.target.value)}
            disabled={loading}
          />
        </div>

        {/* Brand Assets Toggle */}
        <button
          type="button"
          className="flex items-center gap-2 text-slate-400 hover:text-white mb-4 transition-colors"
          onClick={() => setShowAssets(!showAssets)}
        >
          <Upload className="w-4 h-4" />
          <span>Brand Assets (Optional)</span>
          {showAssets ? (
            <ChevronUp className="w-4 h-4" />
          ) : (
            <ChevronDown className="w-4 h-4" />
          )}
        </button>

        {/* Brand Assets Section */}
        {showAssets && (
          <div className="space-y-4 p-4 bg-slate-900/50 rounded-lg mb-6">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Logo URL
              </label>
              <input
                type="url"
                className="input"
                placeholder="https://example.com/logo.png"
                value={logoUrl}
                onChange={(e) => setLogoUrl(e.target.value)}
                disabled={loading}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Product Image URL
              </label>
              <input
                type="url"
                className="input"
                placeholder="https://example.com/product.jpg"
                value={demoImageUrl}
                onChange={(e) => setDemoImageUrl(e.target.value)}
                disabled={loading}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Demo Video URL
              </label>
              <input
                type="url"
                className="input"
                placeholder="https://example.com/demo.mp4"
                value={demoVideoUrl}
                onChange={(e) => setDemoVideoUrl(e.target.value)}
                disabled={loading}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Brand Colors
              </label>
              <div className="flex gap-2">
                {brandColors.map((color, index) => (
                  <input
                    key={index}
                    type="color"
                    value={color}
                    onChange={(e) => {
                      const newColors = [...brandColors];
                      newColors[index] = e.target.value;
                      setBrandColors(newColors);
                    }}
                    className="w-10 h-10 rounded cursor-pointer"
                    disabled={loading}
                  />
                ))}
                {brandColors.length < 3 && (
                  <button
                    type="button"
                    onClick={() => setBrandColors([...brandColors, '#64748b'])}
                    className="w-10 h-10 rounded border-2 border-dashed border-slate-600 text-slate-500 hover:border-slate-500 hover:text-slate-400"
                    disabled={loading}
                  >
                    +
                  </button>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-3 mb-6 text-red-400">
            {error}
          </div>
        )}

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
        <div className="flex items-center gap-2 mb-4">
          <div className="h-px flex-1 bg-gradient-to-r from-transparent via-slate-700 to-transparent" />
          <span className="text-sm font-medium text-slate-500 px-3">Try an example</span>
          <div className="h-px flex-1 bg-gradient-to-r from-transparent via-slate-700 to-transparent" />
        </div>
        <div className="grid gap-3">
          {[
            { text: 'Promote the AI assistant builder to startup founders who use no-code tools. Punchy tone. ₦25,000/day for 5 days.', tag: 'SaaS' },
            { text: 'Advertise the productivity app to remote workers and freelancers. Professional tone. ₦30,000/day for 4 days.', tag: 'App' },
            { text: 'Launch campaign for delivery API targeting e-commerce developers. Technical tone. ₦22,000/day for 5 days.', tag: 'API' },
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
      </div>
    </div>
  );
}
