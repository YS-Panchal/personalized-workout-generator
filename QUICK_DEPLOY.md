# 🚀 Quick Deployment Steps

## TL;DR - Deploy in 5 Minutes

### Step 1: Get New API Key (2 min)
```bash
# Go to: https://aistudio.google.com/app/apikey
# Delete old key
# Create new key
# Copy the key value
```

### Step 2: Test Locally (1 min)
```bash
# Create/update .env file
echo "GEMINI_API_KEY=<YOUR_NEW_KEY>" > .env
echo "FLASK_DEBUG=false" >> .env

# Test
python app.py
# Visit: http://localhost:5000
```

### Step 3: Deploy on Render (2 min)
```
1. Go to: https://render.com
2. Sign up with GitHub
3. Click "New" → "Web Service"
4. Select: personalized-workout-generator repo
5. Configure:
   - Name: workout-generator
   - Build: pip install -r requirements.txt
   - Start: gunicorn app:app
6. Click "Create Web Service"
```

### Step 4: Add Environment Variables (1 min)
```
In Render Dashboard:
1. Click "Environment" (left sidebar)
2. Add three variables:
   - GEMINI_API_KEY = <YOUR_NEW_KEY>
   - FLASK_DEBUG = false
   - SECRET_KEY = <run: python -c "import os; print(os.urandom(24).hex())">
3. Click Save
```

### Step 5: Done! 🎉
- Render builds automatically
- Visit: https://workout-generator.onrender.com
- Your app is live!

---

---

## Deploying on Vercel (what this project actually uses)

The live app runs on Vercel, so these are the variables that matter most. Set them in
**Project → Settings → Environment Variables** for the **Production** (and Preview)
scope, then redeploy:

```bash
GEMINI_API_KEY = <your key from https://aistudio.google.com/app/apikey>
SECRET_KEY     = <python -c "import os; print(os.urandom(24).hex())">   # REQUIRED
FLASK_DEBUG    = false
GEMINI_MODEL   = gemini-flash-latest   # or gemini-3.6-flash / gemini-3.7-flash
```

`SECRET_KEY` is mandatory: without it the app refuses to start in production, because
sessions and CSRF tokens need one stable key across serverless instances.

Verify the deployment:

```bash
curl -I https://<your-app>.vercel.app/          # expect 200
curl https://<your-app>.vercel.app/healthz      # shows key configured + model
```

Full Vercel instructions (including a `/generate` troubleshooting table) are in
[DEPLOYMENT.md](DEPLOYMENT.md).
## Important Security Notes

⚠️ **CRITICAL:**
- Your old key `AIzaSyB7LZHOozevjs1pZFq0pkuPPWomVBht4_E` is COMPROMISED
- YOU MUST get a new key before deploying
- NEVER put keys in code, only in Render Environment Variables

✅ **SAFE:**
- `.env` file is in `.gitignore` (won't upload to GitHub)
- Environment variables are encrypted on Render
- Your new key will only exist on Render's secure servers

---

## After Deployment

### Test the Application
1. Open: https://workout-generator.onrender.com
2. Fill the form
3. Click "Generate Plan"
4. Wait for result
5. Try "Save as PDF"

### Change API Key Later
If needed, update in Render:
1. Dashboard → Environment
2. Update GEMINI_API_KEY value
3. Render auto-restarts with new key

---

## Pricing

| Service | Cost |
|---------|------|
| Render Free Tier | $0/month (limited) |
| Render Starter | $7/month (production) |
| Google Gemini API | Free tier + pay-as-you-go |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "GEMINI_API_KEY not set" | Check Environment Variables in Render |
| App crashes | Check Logs in Render Dashboard |
| PDF not downloading | Refresh page, try different browser |
| Service keeps restarting | Check for syntax errors in app.py |

---

## Files to Know

| File | Purpose |
|------|---------|
| `.env` | Local API keys (DO NOT COMMIT) |
| `.env.example` | Shows what keys you need |
| `render.yaml` | Render deployment config |
| `requirements.txt` | Python packages |
| `app.py` | Main Flask application |
| `DEPLOYMENT.md` | Full deployment guide |

---

## Quick Links

- 🔑 **Get API Key:** https://aistudio.google.com/app/apikey
- ☁️ **Render Signup:** https://render.com
- 📚 **Full Guide:** See DEPLOYMENT.md
- 🐙 **GitHub Repo:** https://github.com/YS-Panchal/personalized-workout-generator
