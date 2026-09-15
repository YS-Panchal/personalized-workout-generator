# Deployment Guide - Render

This guide will help you deploy the Personalized Workout Generator on Render.

---

## Step 1: Get a New API Key (IMPORTANT!)

Since your old API key was exposed, you MUST get a new one:

1. Go to: **https://aistudio.google.com/app/apikey**
2. Delete the old key (if still visible): `AIzaSyB7LZHOozevjs1pZFq0pkuPPWomVBht4_E`
3. Click **"Create API Key"**
4. Copy your NEW API key and keep it safe
5. Save it somewhere secure - you'll need it for Render deployment

---

## Step 2: Prepare Your Local Environment

### Update Your Local `.env` File

Before deploying, update your local `.env` file with the new API key:

```bash
# .env file (never commit this!)
GEMINI_API_KEY=<YOUR_NEW_API_KEY>
FLASK_DEBUG=false
SECRET_KEY=<Your_Random_Secret_Key>
```

**To generate a new SECRET_KEY:**
```bash
python -c "import os; print(os.urandom(24).hex())"
```

### Test Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py

# Visit: http://localhost:5000
```

---

## Step 3: Deploy on Render

### 3.1 Create a Render Account

1. Go to: **https://render.com**
2. Click **Sign Up**
3. Choose **Sign up with GitHub** (easiest option)
4. Authorize Render to access your GitHub account

### 3.2 Create a New Web Service

1. From Render Dashboard, click **New +** → **Web Service**
2. Select your GitHub repository: `personalized-workout-generator`
3. Configure the deployment:

   | Setting | Value |
   |---------|-------|
   | **Name** | `workout-generator` (or your choice) |
   | **Environment** | Python 3 |
   | **Build Command** | `pip install -r requirements.txt` |
   | **Start Command** | `gunicorn app:app` |
   | **Instance Type** | Free (or Starter) |

4. Click **Create Web Service**

### 3.3 Add Environment Variables

⚠️ **CRITICAL STEP - Never put API keys in code!**

1. In your Render dashboard, go to your service: **workout-generator**
2. Click on **Environment** (left sidebar)
3. Add the following environment variables:

   ```
   GEMINI_API_KEY = <YOUR_NEW_API_KEY>
   FLASK_DEBUG = false
   SECRET_KEY = <Generate using: python -c "import os; print(os.urandom(24).hex())">
   ```

4. Click **Save** after each addition

**Example:**
```
GEMINI_API_KEY = AIzaSyC... (your new key)
FLASK_DEBUG = false
SECRET_KEY = a1b2c3d4e5f6... (random 48-character string)
```

---

## Step 4: Monitor Deployment

1. Render will automatically start building
2. Watch the **Logs** tab for build progress
3. Look for: `"Listening on 0.0.0.0:10000"`
4. Once deployed, you'll get a URL like: `https://workout-generator.onrender.com`

### Troubleshooting Build Issues

If deployment fails, check:
- **Logs** tab for error messages
- Ensure all dependencies are in `requirements.txt`
- Verify `render.yaml` is correct
- Check that API key is properly set in Environment Variables

---

## Step 5: Using Your Deployed Application

### Access the App

1. Visit: `https://workout-generator.onrender.com`
2. You should see the Personalized Workout Generator homepage

### How to Use

1. **Fill out the form:**
   - Select Fitness Goal (Fat Loss, Muscle Gain, etc.)
   - Enter Workout Duration (5-180 minutes)
   - Enter Weight (in kg)
   - Enter Height (in cm)
   - Enter Age
   - Select Gender
   - Select Fitness Level
   - (Optional) Add Equipment

2. **Click "Generate Plan"**
   - A loading spinner will appear
   - The AI will generate your personalized plan (usually 10-30 seconds)

3. **View Your Plan**
   - Your workout plan will appear with detailed exercises
   - Exercise demo videos will load (if matched)
   - Click **"Save Workout Plan as PDF"** to download

4. **Download PDF**
   - The PDF will contain your complete workout plan
   - Can be used offline

---

## Step 6: Update API Key Later

### If You Need to Change Your API Key:

1. Get a new API key from: **https://aistudio.google.com/app/apikey**
2. Go to your Render service dashboard
3. Click **Environment**
4. Update the **GEMINI_API_KEY** value
5. Render will automatically restart the service with the new key

---

## Alternative: Deploy on Vercel

Vercel detects the Flask app in `app.py` automatically (no `vercel.json` needed) and
runs it as a Python 3.12 function. The function route shown in the Vercel logs is
`/flask`.

1. Import the GitHub repository at **https://vercel.com/new**
2. Framework preset **Flask** is detected automatically; Vercel installs
   `requirements.txt` for you (the `gunicorn` start command is only used by Render)
3. Go to **Project → Settings → Environment Variables** and add these for the
   **Production** (and Preview) scope:

   | Variable | Value | Why |
   |----------|-------|-----|
   | `GEMINI_API_KEY` | key from https://aistudio.google.com/app/apikey | Gemini access |
   | `SECRET_KEY` | output of `python -c "import os; print(os.urandom(24).hex())"` | **Required in production.** Without it the app refuses to start - sessions and CSRF tokens need one stable key, and a random key per serverless instance makes POSTs fail with "The CSRF token is missing." |
   | `FLASK_DEBUG` | `false` | never enable debug in production |
   | `GEMINI_MODEL` | e.g. `gemini-flash-latest` | pin a model your key can access |
   | `GEMINI_TIMEOUT_MS` | `30000` | per-request timeout in milliseconds |

4. Redeploy so the new variables are picked up.

### Verifying a Vercel deployment

```bash
# Home page (expect 200)
curl -I https://<your-app>.vercel.app/

# Health probe: shows whether the key is configured and which model is used
curl https://<your-app>.vercel.app/healthz

# Which models your API key can actually use (read-only, no quota used)
curl "https://generativelanguage.googleapis.com/v1beta/models?key=$GEMINI_API_KEY"
```

### Troubleshooting /generate

| Symptom | Meaning | Fix |
|---------|---------|-----|
| `503` + "The workout service is not configured correctly" | API key rejected (invalid, revoked, placeholder or whitespace) | rotate the key at https://aistudio.google.com/app/apikey and set it for the Production scope |
| `503` + "The AI model is temporarily unavailable" | the model in `GEMINI_MODEL` is not available to your key | pick a model returned by the models endpoint above |
| `503` + "The service is busy right now" | quota / rate limit reached | wait or enable billing |
| `400` + "The CSRF token is missing" | `SECRET_KEY` is missing or changing between instances | set a fixed `SECRET_KEY` |
| `500` | unexpected internal error | Vercel → Deployments → Logs for the traceback |

Server-side logs always contain the real reason (`Gemini request failed for model ...`
followed by the SDK traceback); users only ever see a safe message.

---
## Security Best Practices

✅ **Do:**
- Keep API keys in environment variables only
- Use different keys for local and production
- Rotate keys regularly
- Use `.env.example` to show what keys are needed
- Store sensitive data only in Render's Environment Variables

❌ **Don't:**
- Commit `.env` file to GitHub
- Share your API key with anyone
- Put API keys in code comments
- Use the same key across environments

---

## Monitoring & Maintenance

### Check Service Status
- Dashboard → Your service → Logs
- Look for errors or unusual activity

### Keep Updated
- Monitor GitHub for updates to dependencies
- Regularly check for security updates
- Test new versions locally before deploying

### Performance
- Free tier has limited resources (512MB memory)
- If you experience slowness, upgrade to Starter plan
- Monitor API usage from Google Cloud Console

---

## Deployment Checklist

- [ ] New API key generated and saved securely
- [ ] `.env` file updated locally with new key
- [ ] Tested locally with new key
- [ ] GitHub repository is up to date
- [ ] Render account created
- [ ] Web service created on Render
- [ ] Environment variables added to Render:
  - [ ] GEMINI_API_KEY
  - [ ] FLASK_DEBUG = false
  - [ ] SECRET_KEY
- [ ] Deployment successful (no errors in logs)
- [ ] Application accessible via Render URL
- [ ] Form submission tested
- [ ] PDF download tested

---

## Troubleshooting

### Issue: "GEMINI_API_KEY not set"
**Solution:** Check Environment Variables in Render dashboard. Ensure `GEMINI_API_KEY` is added and saved.

### Issue: "Application crashes after deployment"
**Solution:** Check Logs tab in Render. Common causes:
- Missing API key
- Missing dependencies (check `requirements.txt`)
- Python version compatibility

### Issue: "PDF download not working"
**Solution:** 
- Ensure security headers allow CDN (already configured)
- Try a different browser
- Check browser console for errors (F12)

### Issue: "Service keeps restarting"
**Solution:**
- Check logs for infinite loops
- Ensure no syntax errors in Python code
- Verify all environment variables are set

---

## Example Deployment Output

```
Build started...
 #1 [build 1/4] FROM python:3.11-slim
 #2 RUN pip install -r requirements.txt
 #3 COPY . .
 #4 Collected 45 packages
    Installing collected packages... done
    
Service deployed successfully!
URL: https://workout-generator.onrender.com
Status: Live
Memory: 512 MB
```

---

## Need Help?

- **Render Docs:** https://render.com/docs
- **Google AI API Issues:** https://aistudio.google.com/support
- **Flask Documentation:** https://flask.palletsprojects.com/
- **GitHub Issues:** Create an issue in your repository

---

## Cost Information

### Render Pricing (as of 2024)
- **Free Tier:** 
  - 512MB memory
  - Auto-pauses after 15 mins of inactivity
  - Limited to 1 service
  
- **Starter Plan:** 
  - $7/month
  - 512MB memory
  - Always running
  - Recommended for production

- **API Costs (Google Gemini):**
  - Free tier: Limited requests
  - Paid: Based on usage (very affordable)

