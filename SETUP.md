# Personalized Workout Generator

A Flask-based web application that generates personalized workout plans using Google's Gemini AI.

## Setup Instructions

### 1. Get Your Gemini API Key

1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Click **"Create API Key"** in the left sidebar
3. A new key will be generated - **copy it**

### 2. Configure the API Key Locally

1. In the project root directory, create a file named `.env`
2. Add the following line:
   ```
   GEMINI_API_KEY=your_copied_api_key_here
   ```
3. Replace `your_copied_api_key_here` with the actual key from step 1
4. **IMPORTANT: Never commit the `.env` file** - it's protected by `.gitignore`

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Application

```bash
python app.py
```

The app will be available at `http://localhost:5000`

## Production Deployment (Render)

When deploying to Render, set the `GEMINI_API_KEY` environment variable in the Render dashboard:

1. Go to your Render service settings
2. Navigate to **Environment**
3. Add a new environment variable:
   - **Key:** `GEMINI_API_KEY`
   - **Value:** Your Gemini API key

The `render.yaml` file is already configured to use this variable.

## Security Notes

⚠️ **NEVER:**
- Commit your `.env` file to Git
- Share your API key publicly
- Push code that contains exposed API keys

✅ **DO:**
- Keep your API key in the local `.env` file
- Use `.env.example` as a template (it's safe to commit)
- Rotate your API key if it's accidentally exposed

## Files

- `.env` - Local configuration (ignored by git) - **Create this file locally**
- `.env.example` - Template file showing required variables (safe to commit)
- `.gitignore` - Prevents `.env` from being committed
