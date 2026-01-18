# Career Pathway Backend - Setup Guide

## Overview

This backend solves Zapier's 30-second timeout issue by:
1. Receiving your variables via webhook (instant response)
2. Processing with Claude Opus/Sonnet in the background (can take 60-90 seconds)
3. Returning results when polled

---

## Files Included

```
career-pathway-backend/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── Procfile           # Heroku process configuration
└── runtime.txt        # Python version specification
```

---

## Step 1: Deploy to Heroku

### Option A: Using Heroku CLI

```bash
# 1. Create a new directory and add files
mkdir career-pathway-backend
cd career-pathway-backend

# 2. Initialize git
git init

# 3. Add all files (app.py, requirements.txt, Procfile, runtime.txt)

# 4. Login to Heroku
heroku login

# 5. Create new Heroku app
heroku create your-app-name

# 6. Set your Anthropic API key
heroku config:set ANTHROPIC_API_KEY=your-anthropic-api-key-here

# 7. Deploy
git add .
git commit -m "Initial deploy"
git push heroku main

# 8. Verify it's running
heroku open
```

### Option B: Using Heroku Dashboard

1. Go to https://dashboard.heroku.com
2. Click "New" → "Create new app"
3. Name your app (e.g., `career-pathway-api`)
4. Connect to GitHub or use Heroku Git
5. Upload the files
6. Go to "Settings" → "Config Vars"
7. Add: `ANTHROPIC_API_KEY` = `your-anthropic-api-key`
8. Deploy

---

## Step 2: Update Your Zapier Workflow

### Replace "AI by Zapier" with these 3 steps:

#### Step X: Webhooks by Zapier (POST) - Submit Job

```
Action: POST
URL: https://your-app-name.herokuapp.com/submit
Payload Type: JSON
Data:
{
  "name": "{{step_form_name}}",
  "profession": "{{step_form_profession}}",
  "great_at": "{{step_form_great_at}}",
  "challenges": "{{step_form_challenges}}",
  "wins": "{{step_form_wins}}",
  "goals": "{{step_form_goals}}",
  "location": "{{step_form_location}}",
  "contact_email": "{{step_form_contact_email}}",
  "headline": "{{step_apify_headline}}",
  "about": "{{step_apify_about}}",
  "experience": "{{step_apify_experience}}",
  "education": "{{step_apify_education}}",
  "skills_analysis_output": "{{step_skills_output}}"
}
```

**Response:** Returns `job_id` immediately

---

#### Step X+1: Delay by Zapier

```
Delay For: 2 minutes
```

(Adjust based on typical processing time - start with 2 min, reduce if faster)

---

#### Step X+2: Webhooks by Zapier (GET) - Get Result

```
Action: GET
URL: https://your-app-name.herokuapp.com/result/{{step_submit_job_id}}
```

**Response:** Returns the full Claude analysis in `result` field

---

## Step 3: Variable Mapping Reference

Map these fields from your existing Zap steps:

| Backend Variable | Source in Zapier |
|-----------------|------------------|
| `name` | Form step → name field |
| `profession` | Form step → profession field |
| `great_at` | Form step → great_at field |
| `challenges` | Form step → challenges field |
| `wins` | Form step → wins field |
| `goals` | Form step → goals field |
| `location` | Form step → location field |
| `contact_email` | Form step → contact_email field |
| `headline` | Apify Code step → headline |
| `about` | Apify Code step → about |
| `experience` | Apify Code step → experience |
| `education` | Apify Code step → education |
| `skills_analysis_output` | Skills analysis step → output |

---

## Step 4: Testing

### Test the endpoints directly:

```bash
# Health check
curl https://your-app-name.herokuapp.com/health

# Submit a test job
curl -X POST https://your-app-name.herokuapp.com/submit \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "profession": "Software Engineer",
    "great_at": "Problem solving",
    "challenges": "Canadian experience",
    "wins": "Led team projects",
    "goals": "Get P.Eng license",
    "location": "Toronto, Ontario",
    "contact_email": "test@example.com",
    "headline": "Senior Software Engineer",
    "about": "10 years experience in software development",
    "experience": "Experience 1: Software Engineer at Google",
    "education": "Education 1: BS Computer Science from MIT",
    "skills_analysis_output": "Strong technical skills"
  }'

# Get result (use job_id from above response)
curl https://your-app-name.herokuapp.com/result/YOUR_JOB_ID
```

---

## Changing the AI Model

In `app.py`, find this line:

```python
model="claude-sonnet-4-20250514",  # Use claude-opus-4-20250514 for best quality
```

Change to:
- `claude-opus-4-20250514` - Best quality, slower, more expensive
- `claude-sonnet-4-20250514` - Good balance (recommended)
- `claude-haiku-4-20250514` - Fastest, cheapest, lower quality

---

## Troubleshooting

### "Job still processing" after 2 minutes
- Increase delay to 3 minutes
- Check Heroku logs: `heroku logs --tail`

### Empty or error response
- Verify ANTHROPIC_API_KEY is set correctly
- Check if API key has sufficient credits

### Zapier webhook timeout
- The /submit endpoint returns immediately, so this shouldn't happen
- If it does, check Heroku app is running: `heroku ps`

---

## Cost Estimates

- **Heroku**: Free tier (Eco dynos) or ~$7/month for basic
- **Anthropic API**: ~$0.015-0.075 per request depending on model
  - Opus: ~$0.075 per career report
  - Sonnet: ~$0.015 per career report

---

## Production Improvements (Optional)

For higher volume, consider:

1. **Redis for job storage** (current uses in-memory, resets on dyno restart)
```bash
heroku addons:create heroku-redis:mini
```

2. **Webhook callback** instead of polling (more efficient)

3. **Queue system** (Redis Queue or Celery) for better job management

---

## Support

If you need help:
1. Check Heroku logs: `heroku logs --tail`
2. Test endpoints with curl first
3. Verify all environment variables are set
