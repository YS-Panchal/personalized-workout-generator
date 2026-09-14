# SECURITY CONFIGURATION GUIDE

## Overview
This document outlines all security measures implemented in the Personalized Workout Generator and how to properly configure them.

---

## 🔐 Environment Variables

### Required Variables

#### 1. `GEMINI_API_KEY` (REQUIRED)
- **Purpose:** API key for Google Gemini AI
- **Source:** https://aistudio.google.com/app/apikey
- **Location:** Store in `.env` file (never commit)
- **Example:**
  ```
  GEMINI_API_KEY=AIzaSyD...
  ```
- **Security:** Must be kept secret; never expose in code or logs

#### 2. `FLASK_DEBUG` (RECOMMENDED)
- **Purpose:** Enable/disable Flask debug mode
- **Default:** `false` (recommended for all environments)
- **Values:**
  - `false` - Production mode (secure, no stack traces)
  - `true` - Development only (shows errors, enables auto-reload)
- **Example:**
  ```
  FLASK_DEBUG=false
  ```
- **⚠️ WARNING:** Never set to `true` in production!

#### 3. `SECRET_KEY` (REQUIRED)
- **Purpose:** Session management and CSRF token signing
- **How to Generate:**
  ```bash
  python -c "import os; print(os.urandom(24).hex())"
  ```
- **Example:**
  ```
  SECRET_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0
  ```
- **Security:** Must be random and kept secret; change regularly

---

## 🛡️ Security Features Implemented

### 1. API Key Protection ✅
- API key loaded from environment variables only
- `.env` file excluded from git via `.gitignore`
- `.env.example` template provided for developers
- No hardcoded keys in code
- Error messages never reveal API key details

**Verification:**
```bash
# Verify .env is in .gitignore
grep "\.env" .gitignore

# Verify no API key in code
grep -r "AIzaSy" .
```

### 2. Input Validation ✅
- All form inputs validated server-side
- Range checks: age (13-120), weight (20-300kg), height (100-250cm), time (5-180 min)
- Type validation: numeric fields must be numbers
- Enum validation: goal, gender, level must be from allowed list
- Length validation: equipment field max 100 characters

**Key Function:**
```python
def validate_inputs(data):
    # Returns list of validation errors
```

### 3. CSRF Protection ✅
- Flask-WTF with CSRF token validation
- All POST requests require valid CSRF token
- Token automatically included in forms
- Configurable cookie settings:
  - `SESSION_COOKIE_SECURE=True` - HTTPS only
  - `SESSION_COOKIE_HTTPONLY=True` - Prevent JS access
  - `SESSION_COOKIE_SAMESITE='Lax'` - CSRF prevention

### 4. XSS Prevention ✅
- HTML output sanitized with `bleach` library
- Markdown converted safely
- Only safe HTML tags allowed: `<p>`, `<h1-h6>`, `<ul>`, `<ol>`, `<li>`, `<br>`, `<strong>`, `<em>`, `<u>`
- Dangerous tags stripped: `<script>`, `<iframe>`, `<style>`, etc.

**Implementation:**
```python
html_workout = bleach.clean(
    markdown.markdown(response_text),
    tags=['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'br', 'strong', 'em', 'u'],
    strip=True
)
```

### 5. Security Headers ✅
Applied to all responses:
- `X-Content-Type-Options: nosniff` - Prevent MIME type sniffing
- `X-Frame-Options: SAMEORIGIN` - Prevent clickjacking
- `X-XSS-Protection: 1; mode=block` - Enable browser XSS filter
- `Strict-Transport-Security` - Enforce HTTPS
- `Content-Security-Policy` - Restrict resource loading

**Verification:**
```bash
curl -i http://localhost:5000 | grep -i "^X-"
```

### 6. Rate Limiting ✅
- Global: 200 requests/day, 50 requests/hour per IP
- Generate endpoint: 10 requests/minute per IP
- Prevents API abuse and DoS attacks

**Configuration in app.py:**
```python
limiter = Limiter(app=app, key_func=get_remote_address)
@app.route('/generate', methods=['POST'])
@limiter.limit("10 per minute")
def generate():
    ...
```

### 7. Proper Logging ✅
- Uses Python `logging` module (not `print()`)
- Appropriate log levels: INFO, WARNING, ERROR
- Never logs sensitive data (API keys, user inputs)
- Structured logging with timestamps

**Log Examples:**
```
2026-09-14 10:30:45,123 - __main__ - INFO - Successfully generated workout plan
2026-09-14 10:31:20,456 - __main__ - WARNING - Invalid input: ['Invalid fitness goal']
2026-09-14 10:32:00,789 - __main__ - ERROR - Error generating workout: Timeout
```

### 8. Error Handling ✅
- Generic error messages returned to user
- Exception details logged server-side only
- No stack traces exposed to frontend
- Proper HTTP status codes (400, 500)

**Example:**
```python
except Exception as e:
    logger.error(f"Error generating workout: {str(type(e).__name__)}")
    return "An unexpected error occurred. Please try again.", 500
```

### 9. API Timeouts ✅
- Gemini API calls have 30-second timeout
- Prevents hanging requests

```python
response = model.generate_content(
    prompt, 
    request_options={"timeout": 30}
)
```

### 10. Frontend Security ✅
- ✅ No API key exposed in HTML
- ✅ No JavaScript making direct API calls
- ✅ All API requests go through Flask backend
- ✅ Input validation on both client AND server
- ✅ CSRF tokens in forms
- ✅ Secure Content-Security-Policy header

---

## 📋 Deployment Security Checklist

### Before Production Deployment:

- [ ] `FLASK_DEBUG=false` is set in production environment
- [ ] `SECRET_KEY` is set to a secure random value
- [ ] `GEMINI_API_KEY` is set in production environment
- [ ] `.env` file is NOT committed to git
- [ ] `.env.example` is committed to git
- [ ] HTTPS is enabled (Render handles this automatically)
- [ ] Environment variables are set in Render dashboard
- [ ] Application runs with `gunicorn` (not Flask dev server)
- [ ] No debug mode enabled
- [ ] Logs are monitored for errors

### Render Deployment Setup:

1. Go to your Render dashboard
2. Select your service
3. Go to **Environment** tab
4. Add these environment variables:
   ```
   GEMINI_API_KEY = [your-api-key]
   SECRET_KEY = [generated-secret-key]
   FLASK_DEBUG = false
   ```
5. Click **Save**
6. Redeployed service will use new environment variables

---

## 🔍 Security Verification Steps

### Test 1: Verify API Key is Not Exposed
```bash
# Check code for hardcoded keys
grep -r "AIzaSy" . --exclude-dir=.git

# Should return: No matches

# Check .env is ignored
cat .gitignore | grep ".env"

# Should include: .env and .env.local
```

### Test 2: Verify No Debug Mode in Production
```bash
# Check app.py
grep "debug=True" app.py

# Should return: Only in commented security notes or False

# Check render.yaml
grep "FLASK_DEBUG" render.yaml

# Should show: FLASK_DEBUG value is false or sync: false
```

### Test 3: Verify CSRF Protection
```bash
# Make POST request without CSRF token
curl -X POST http://localhost:5000/generate

# Should return: 400 Bad Request (CSRF token validation failed)
```

### Test 4: Verify Input Validation
```bash
# Send invalid age (should fail)
curl -X POST http://localhost:5000/generate \
  -d "goal=fat loss&time=30&weight=75&height=180&age=200&gender=male&level=beginner" \
  -H "X-CSRFToken: valid-token"

# Should return: 400 Bad Request with error message
```

### Test 5: Verify Security Headers
```bash
curl -i http://localhost:5000

# Should include:
# X-Content-Type-Options: nosniff
# X-Frame-Options: SAMEORIGIN
# X-XSS-Protection: 1; mode=block
# Content-Security-Policy: ...
```

---

## 🚨 Common Security Mistakes to Avoid

### ❌ DO NOT:
1. Set `FLASK_DEBUG=true` in production
2. Hardcode API keys in code
3. Commit `.env` file to git
4. Disable CSRF protection
5. Trust user input without validation
6. Log sensitive data
7. Use `print()` for debugging in production
8. Return detailed error messages to users
9. Run Flask dev server in production (use gunicorn)
10. Disable security headers

### ✅ DO:
1. Keep API keys in environment variables
2. Use `.env.example` as template
3. Validate all inputs server-side
4. Log errors safely
5. Return generic error messages
6. Use proper logging module
7. Run with gunicorn in production
8. Monitor error logs
9. Rotate secrets periodically
10. Use HTTPS everywhere

---

## 📚 Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Flask Security](https://flask.palletsprojects.com/security/)
- [Flask-WTF CSRF Documentation](https://flask-wtf.readthedocs.io/en/stable/csrf/)
- [Content Security Policy Guide](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)
- [Python Logging Documentation](https://docs.python.org/3/library/logging.html)

---

## Contact & Support

For security concerns or vulnerabilities, please report privately to the development team.

**Last Updated:** 2026-09-14  
**Version:** 1.0
