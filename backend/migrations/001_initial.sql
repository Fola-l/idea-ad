-- idea-Ad Database Schema
-- Run this SQL in your Supabase SQL editor to create all required tables

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Ad runs table - stores all ad generation jobs
CREATE TABLE IF NOT EXISTS ad_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id TEXT UNIQUE NOT NULL,
    prompt TEXT NOT NULL,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'generating', 'preview', 'deploying', 'live', 'failed')),
    ad_copy JSONB,
    audience JSONB,
    campaign_settings JSONB,
    creative_urls JSONB,
    meta_ids JSONB,
    creative_brief TEXT,
    voiceover_script TEXT,
    image_prompt TEXT,
    format TEXT CHECK (format IN ('image', 'video')),
    sandbox_mode BOOLEAN DEFAULT true,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Interest cache table - caches resolved Meta interest IDs
CREATE TABLE IF NOT EXISTS interest_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    interest_name TEXT UNIQUE NOT NULL,
    interest_id TEXT NOT NULL,
    audience_size BIGINT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Brand profiles table - saves brand kits for reuse
CREATE TABLE IF NOT EXISTS brand_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    logo_url TEXT,
    colors JSONB,
    default_destination_url TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_ad_runs_job_id ON ad_runs(job_id);
CREATE INDEX IF NOT EXISTS idx_ad_runs_status ON ad_runs(status);
CREATE INDEX IF NOT EXISTS idx_ad_runs_created_at ON ad_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_interest_cache_name ON interest_cache(interest_name);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for ad_runs updated_at
DROP TRIGGER IF EXISTS update_ad_runs_updated_at ON ad_runs;
CREATE TRIGGER update_ad_runs_updated_at
    BEFORE UPDATE ON ad_runs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Storage buckets (run these in Supabase dashboard or via API)
-- Note: Storage buckets must be created via Supabase dashboard:
-- 1. Go to Storage in your Supabase project
-- 2. Create bucket named 'creatives' (for generated images/videos)
-- 3. Create bucket named 'uploads' (for user-uploaded demos and logos)
-- 4. Set both buckets to public access for serving assets

-- RLS Policies (optional - enable if you want row level security)
-- ALTER TABLE ad_runs ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE interest_cache ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE brand_profiles ENABLE ROW LEVEL SECURITY;

-- Grant access (for public access without auth)
-- CREATE POLICY "Allow public read access" ON ad_runs FOR SELECT USING (true);
-- CREATE POLICY "Allow public insert access" ON ad_runs FOR INSERT WITH CHECK (true);
-- CREATE POLICY "Allow public update access" ON ad_runs FOR UPDATE USING (true);
