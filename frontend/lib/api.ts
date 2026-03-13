// Call backend directly to avoid Next.js proxy timeout issues with long-running requests
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface GenerateRequest {
  prompt: string;
  brand_colors?: string[];
  logo_url?: string;
  demo_video_url?: string;
  demo_image_url?: string;
  destination_url?: string;
}

export interface AdCopy {
  headline: string;
  body: string;
  cta: string;
}

export interface GeoLocation {
  key: string;
  radius?: number;
  distance_unit?: string;
}

export interface GeoLocations {
  countries: string[];
  cities?: GeoLocation[];
}

export interface CoreAudience {
  age_min: number;
  age_max: number;
  genders: number[];
  geo_locations: GeoLocations;
  locales: number[];
}

export interface Interest {
  id?: string;
  name: string;
  relevance?: string;
  reasoning?: string;
}

export interface Behavior {
  name: string;
  reasoning?: string;
}

export interface Audience {
  core_audience: CoreAudience;
  interests: Interest[];
  behaviors: Behavior[];
  excluded_audiences: { name: string; reasoning: string }[];
  audience_rationale: string;
  targeting_confidence: string;
  estimated_audience_size_note: string;
  budget_fit_note: string;
  suggested_follow_up_audiences: string[];
}

export interface UTMParams {
  utm_source: string;
  utm_medium: string;
  utm_campaign: string;
  utm_content: string;
  utm_term: string;
}

export interface CampaignSettings {
  objective: string;
  daily_budget: number;
  duration_days: number;
  start_paused: boolean;
  destination_url: string;
  utm_params: UTMParams;
}

export interface CreativeUrls {
  image_url?: string;
  video_url?: string;
  voiceover_url?: string;
}

export interface GenerateResponse {
  job_id: string;
  ad_copy: AdCopy;
  audience: Audience;
  campaign_settings: CampaignSettings;
  creative_brief: string;
  voiceover_script?: string;
  image_prompt?: string;
  format: 'image' | 'video';
}

export interface CreativeResponse {
  job_id: string;
  status: string;
  image_url?: string;
  video_url?: string;
  voiceover_url?: string;
}

export interface PreviewResponse {
  job_id: string;
  status: string;
  prompt: string;
  ad_copy?: AdCopy;
  audience?: Audience;
  campaign_settings?: CampaignSettings;
  creative_urls?: CreativeUrls;
  creative_brief?: string;
  voiceover_script?: string;
  format?: string;
}

export interface DeployRequest {
  job_id: string;
  approved_copy: AdCopy;
  approved_audience: Audience;
  approved_settings: CampaignSettings;
  privacy_policy_url?: string;
  sandbox_mode: boolean;
}

export interface DeployResponse {
  job_id: string;
  status: string;
  campaign_id?: string;
  adset_id?: string;
  creative_id?: string;
  ad_id?: string;
  error?: string;
}

export interface StatusResponse {
  ad_id: string;
  effective_status?: string;
  configured_status?: string;
  ad_review_feedback?: Record<string, unknown>;
  created_at?: string;
  campaign_id?: string;
  adset_id?: string;
}

export interface ActivateResponse {
  ad_id: string;
  success: boolean;
  effective_status?: string;
  configured_status?: string;
  campaign_activated: boolean;
  adset_activated: boolean;
  ad_activated: boolean;
  error?: string;
}

export interface AdRun {
  id: string;
  job_id: string;
  prompt: string;
  status: string;
  ad_copy?: AdCopy;
  audience?: Audience;
  campaign_settings?: CampaignSettings;
  creative_urls?: CreativeUrls;
  meta_ids?: {
    campaign_id?: string;
    adset_id?: string;
    creative_id?: string;
    ad_id?: string;
  };
  sandbox_mode: boolean;
  created_at: string;
  updated_at: string;
}

async function fetchAPI<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => null);
      const errorMessage = errorData?.detail || errorData?.message || `HTTP ${response.status}`;
      throw new Error(typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage));
    }

    return response.json();
  } catch (error) {
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new Error('Network error - backend may be unavailable');
    }
    throw error;
  }
}

export async function generateAd(request: GenerateRequest): Promise<GenerateResponse> {
  return fetchAPI('/api/generate', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function generateCreative(jobId: string): Promise<CreativeResponse> {
  return fetchAPI('/api/creative', {
    method: 'POST',
    body: JSON.stringify({ job_id: jobId }),
  });
}

export async function getPreview(jobId: string): Promise<PreviewResponse> {
  return fetchAPI(`/api/preview/${jobId}`);
}

export async function deployAd(request: DeployRequest): Promise<DeployResponse> {
  return fetchAPI('/api/deploy', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function getAdStatus(adId: string): Promise<StatusResponse> {
  return fetchAPI(`/api/status/${adId}`);
}

export async function activateAd(adId: string): Promise<ActivateResponse> {
  return fetchAPI(`/api/activate/${adId}`, {
    method: 'POST',
  });
}

export async function getHistory(limit: number = 50): Promise<{ runs: AdRun[] }> {
  return fetchAPI(`/api/history?limit=${limit}`);
}

export async function regenerateImage(jobId: string): Promise<{ image_url: string }> {
  return fetchAPI(`/api/regenerate-image?job_id=${jobId}`, {
    method: 'POST',
  });
}

export async function regenerateVoiceover(jobId: string): Promise<{ voiceover_url: string }> {
  return fetchAPI(`/api/regenerate-voiceover?job_id=${jobId}`, {
    method: 'POST',
  });
}
