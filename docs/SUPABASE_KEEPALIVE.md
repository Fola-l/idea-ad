# Supabase Keep-Alive Setup

## Problem
Supabase free tier pauses projects after **7 days of inactivity**. This causes database queries to fail until the project is manually reactivated.

## Solution
Use a free external cron service to ping your backend's `/health` endpoint every 5 days, which queries the database and keeps Supabase active.

---

## Step 1: Health Endpoint

Your backend already has a health check endpoint at:
```
https://your-backend-url.onrender.com/health
```

This endpoint:
- Returns `200 OK` status
- Executes a simple database query to keep Supabase active
- Prevents the 7-day inactivity pause

---

## Step 2: Set Up Free Cron Service

Choose one of these free options:

### Option A: cron-job.org (Recommended)
**Free tier**: Unlimited jobs, 1-minute minimum interval

1. Go to [cron-job.org](https://cron-job.org)
2. Sign up for free
3. Create new cron job:
   - **Title**: `Supabase Keep-Alive`
   - **URL**: `https://your-backend-url.onrender.com/health`
   - **Schedule**: Every 5 days (or `0 0 */5 * *` in cron syntax)
   - **Method**: GET
   - **Enable notifications**: OFF (optional)
4. Save and activate

### Option B: UptimeRobot
**Free tier**: 50 monitors, 5-minute minimum interval

1. Go to [uptimerobot.com](https://uptimerobot.com)
2. Sign up for free
3. Add new monitor:
   - **Monitor Type**: HTTP(s)
   - **Friendly Name**: `idea-ad Health Check`
   - **URL**: `https://your-backend-url.onrender.com/health`
   - **Monitoring Interval**: Every 5 days (select closest available, typically shows as "Custom")
4. Create monitor

### Option C: GitHub Actions (Developer-Friendly)
**Free tier**: 2000 minutes/month

Create `.github/workflows/keepalive.yml`:

```yaml
name: Supabase Keep-Alive

on:
  schedule:
    # Run every 5 days at 00:00 UTC
    - cron: '0 0 */5 * *'
  workflow_dispatch: # Allow manual trigger

jobs:
  ping:
    runs-on: ubuntu-latest
    steps:
      - name: Ping health endpoint
        run: |
          curl -f https://your-backend-url.onrender.com/health || exit 1
```

Push to GitHub and the workflow will run automatically.

---

## Step 3: Verify Setup

1. Check your cron service dashboard to confirm the job ran successfully
2. Visit your health endpoint manually: `https://your-backend-url.onrender.com/health`
3. Expected response:
   ```json
   {
     "status": "ok",
     "service": "idea-ad",
     "database": "connected"
   }
   ```

---

## Recommended Schedule

| Interval | Reason |
|----------|--------|
| Every 5 days | Safe margin before 7-day pause |
| Every 3 days | Extra safety buffer (recommended) |
| Daily | Overkill but ensures 100% uptime |

---

## Cost: $0
All services listed are completely free for this use case.

---

## Troubleshooting

**Q: My Supabase still paused after setup**
- Check cron job logs to confirm it's running
- Verify the URL is correct (no typos)
- Ensure the health endpoint returns 200 status

**Q: Health endpoint returns error**
- Check Supabase connection settings
- Verify environment variables are set correctly
- Check Render logs for backend errors

**Q: I'm getting too many requests errors**
- Reduce frequency (5 days is sufficient)
- Most free tiers allow 1 request/5 days easily

