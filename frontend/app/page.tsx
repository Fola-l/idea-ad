'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Sparkles, Upload, ChevronDown, ChevronUp, Loader2, Zap, Target, TrendingUp, X } from 'lucide-react';
import { generateAd, generateCreative } from '@/lib/api';
import { uploadFile } from '@/lib/storage';

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
  const [showExamples, setShowExamples] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('');
  const [error, setError] = useState('');

  // Brand assets state
  const [logoUrl, setLogoUrl] = useState('');
  const [demoImageUrl, setDemoImageUrl] = useState('');
  const [demoVideoUrl, setDemoVideoUrl] = useState('');
  const [brandColors, setBrandColors] = useState<string[]>(['#0ea5e9']);

  // File upload state
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState<{ logo?: boolean; image?: boolean; video?: boolean }>({});

  const handleFileUpload = async (file: File, type: 'logo' | 'image' | 'video') => {
    setUploading({ ...uploading, [type]: true });
    try {
      const url = await uploadFile(file, type);

      if (type === 'logo') {
        setLogoUrl(url);
        setLogoFile(file);
      } else if (type === 'image') {
        setDemoImageUrl(url);
        setImageFile(file);
      } else {
        setDemoVideoUrl(url);
        setVideoFile(file);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading({ ...uploading, [type]: false });
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>, type: 'logo' | 'image' | 'video') => {
    const file = e.target.files?.[0];
    if (file) {
      await handleFileUpload(file, type);
    }
  };

  const removeFile = (type: 'logo' | 'image' | 'video') => {
    if (type === 'logo') {
      setLogoFile(null);
      setLogoUrl('');
    } else if (type === 'image') {
      setImageFile(null);
      setDemoImageUrl('');
    } else {
      setVideoFile(null);
      setDemoVideoUrl('');
    }
  };

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
            {/* Logo Upload */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Logo
              </label>
              {!logoFile ? (
                <label className="flex items-center justify-center gap-2 px-4 py-3 border-2 border-dashed border-slate-700 hover:border-slate-600 rounded-lg cursor-pointer transition-colors">
                  <Upload className="w-4 h-4 text-slate-400" />
                  <span className="text-slate-400 text-sm">
                    {uploading.logo ? 'Uploading...' : 'Upload logo (PNG, JPG, max 5MB)'}
                  </span>
                  <input
                    type="file"
                    className="hidden"
                    accept="image/png,image/jpeg,image/jpg,image/webp"
                    onChange={(e) => handleFileChange(e, 'logo')}
                    disabled={loading || uploading.logo}
                  />
                </label>
              ) : (
                <div className="flex items-center justify-between px-4 py-3 bg-slate-800/50 border border-slate-700 rounded-lg">
                  <div className="flex items-center gap-2">
                    <Upload className="w-4 h-4 text-green-400" />
                    <span className="text-slate-300 text-sm">{logoFile.name}</span>
                  </div>
                  <button
                    onClick={() => removeFile('logo')}
                    className="text-slate-400 hover:text-red-400 transition-colors"
                    disabled={loading}
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>

            {/* Product Image Upload */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Product Image
              </label>
              {!imageFile ? (
                <label className="flex items-center justify-center gap-2 px-4 py-3 border-2 border-dashed border-slate-700 hover:border-slate-600 rounded-lg cursor-pointer transition-colors">
                  <Upload className="w-4 h-4 text-slate-400" />
                  <span className="text-slate-400 text-sm">
                    {uploading.image ? 'Uploading...' : 'Upload image (PNG, JPG, max 10MB)'}
                  </span>
                  <input
                    type="file"
                    className="hidden"
                    accept="image/png,image/jpeg,image/jpg,image/webp"
                    onChange={(e) => handleFileChange(e, 'image')}
                    disabled={loading || uploading.image}
                  />
                </label>
              ) : (
                <div className="flex items-center justify-between px-4 py-3 bg-slate-800/50 border border-slate-700 rounded-lg">
                  <div className="flex items-center gap-2">
                    <Upload className="w-4 h-4 text-green-400" />
                    <span className="text-slate-300 text-sm">{imageFile.name}</span>
                  </div>
                  <button
                    onClick={() => removeFile('image')}
                    className="text-slate-400 hover:text-red-400 transition-colors"
                    disabled={loading}
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>

            {/* Demo Video Upload */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Demo Video
              </label>
              {!videoFile ? (
                <label className="flex items-center justify-center gap-2 px-4 py-3 border-2 border-dashed border-slate-700 hover:border-slate-600 rounded-lg cursor-pointer transition-colors">
                  <Upload className="w-4 h-4 text-slate-400" />
                  <span className="text-slate-400 text-sm">
                    {uploading.video ? 'Uploading...' : 'Upload video (MP4, max 50MB)'}
                  </span>
                  <input
                    type="file"
                    className="hidden"
                    accept="video/mp4,video/quicktime,video/x-msvideo,video/webm"
                    onChange={(e) => handleFileChange(e, 'video')}
                    disabled={loading || uploading.video}
                  />
                </label>
              ) : (
                <div className="flex items-center justify-between px-4 py-3 bg-slate-800/50 border border-slate-700 rounded-lg">
                  <div className="flex items-center gap-2">
                    <Upload className="w-4 h-4 text-green-400" />
                    <span className="text-slate-300 text-sm">{videoFile.name}</span>
                  </div>
                  <button
                    onClick={() => removeFile('video')}
                    className="text-slate-400 hover:text-red-400 transition-colors"
                    disabled={loading}
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              )}
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
        )}
      </div>
    </div>
  );
}
