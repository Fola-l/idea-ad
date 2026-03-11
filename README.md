# idea-Ad

AI-powered Facebook ad generation and deployment. Describe your product, get a complete ad campaign deployed to Meta Ads.

## Features

- **Single Prompt → Full Campaign**: Just describe your product and audience
- **AI-Generated Creative**: DALL-E 3 images, OpenAI TTS voiceovers, ffmpeg video assembly
- **Automated Audience Intelligence**: Claude analyzes your prompt to create precise UK-focused targeting
- **Preview & Edit**: Review and customize everything before deployment
- **Direct Meta Deployment**: Creates campaigns, ad sets, creatives, and ads via Meta Marketing API

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: Next.js 14 (App Router) + Tailwind CSS
- **AI**: Anthropic Claude, OpenAI DALL-E 3 + TTS
- **Database**: Supabase
- **Deployment**: Render (backend) + Vercel (frontend)

## Project Structure

```
idea-ad/
├── frontend/           # Next.js 14 app
│   ├── app/           # App Router pages
│   ├── components/    # React components
│   └── lib/           # API client
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI routes
│   │   ├── config.py         # Environment config
│   │   ├── models.py         # Pydantic models
│   │   ├── services/         # Business logic
│   │   ├── utils/            # Utilities
│   │   └── db/               # Supabase client
│   ├── migrations/           # SQL migrations
│   └── requirements.txt
└── .env.example
```

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- ffmpeg installed locally
- Supabase project
- API keys for: Anthropic, OpenAI, Meta Marketing API

### 1. Clone and Install

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

### 2. Environment Variables

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

Required variables:
- `ANTHROPIC_API_KEY` - Claude API key
- `OPENAI_API_KEY` - OpenAI API key (DALL-E + TTS)
- `META_APP_ID` - Meta app ID
- `META_APP_SECRET` - Meta app secret
- `META_SYSTEM_TOKEN` - Non-expiring system user token
- `META_AD_ACCOUNT_ID_SANDBOX` - Sandbox ad account (act_XXX)
- `META_AD_ACCOUNT_ID_LIVE` - Production ad account
- `META_PAGE_ID` - Facebook page ID
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_ANON_KEY` - Supabase anon key

### 3. Database Setup

Run the migration in Supabase SQL editor:

```bash
# Copy contents of backend/migrations/001_initial.sql
# Paste into Supabase SQL editor and run
```

Create storage buckets in Supabase dashboard:
- `creatives` (public)
- `uploads` (public)

### 4. Run Locally

```bash
# Terminal 1 - Backend
cd backend
uvicorn app.main:app --reload

# Terminal 2 - Frontend
cd frontend
npm run dev
```

Visit http://localhost:3000

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/generate` | POST | Generate ad strategy from prompt |
| `/api/creative` | POST | Generate creative assets |
| `/api/preview/{job_id}` | GET | Get preview data |
| `/api/deploy` | POST | Deploy to Meta Ads |
| `/api/status/{ad_id}` | GET | Get ad status from Meta |
| `/api/history` | GET | List past ad runs |
| `/health` | GET | Health check |

## Meta API Setup

1. Create a Meta App at developers.facebook.com
2. Add "Marketing API" product
3. Create a System User in Business Settings
4. Generate a non-expiring token with these permissions:
   - `ads_management`
   - `ads_read`
   - `business_management`
   - `pages_read_engagement`
5. Create a sandbox ad account for testing

## Deployment

### Backend (Render)

1. Push code to GitHub
2. Create new Web Service on Render
3. Connect repo, select `backend` directory
4. Set environment variables
5. Deploy

### Frontend (Vercel)

1. Import repo to Vercel
2. Set root directory to `frontend`
3. Add `NEXT_PUBLIC_API_URL` env var pointing to Render URL
4. Deploy

## Usage

1. Enter a prompt describing your product and target audience
2. Optionally add brand assets (logo, demo video, product image)
3. Click "Generate Ad"
4. Review and edit the generated ad copy, audience, and settings
5. Click "Deploy to Facebook"
6. Monitor status in the dashboard

## Important Notes

- All ads are created as **PAUSED** - activate in Meta Ads Manager
- Budget is in GBP (£)
- Default targeting is UK market
- Video ads include Ken Burns effect and TTS voiceover
- Interest IDs are resolved via Meta Targeting Search API

## License

MIT
