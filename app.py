from flask import Flask, render_template, request, jsonify
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import google.genai as genai
from google.genai import types as genai_types
import markdown
import bleach
import re
import os
import logging
from dotenv import load_dotenv
from io import BytesIO
from weasyprint import HTML
from flask import send_file

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# ✅ SECURITY: Configure secure session cookies
app.config['SESSION_COOKIE_SECURE'] = True  # Only send over HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JS access
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection

# ✅ SECURITY: Initialize CSRF protection
csrf = CSRFProtect(app)

# ✅ SECURITY: Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# ✅ SECURITY: Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ✅ SECURITY: Configure debug mode from environment
DEBUG_MODE = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
app.debug = DEBUG_MODE

# ✅ SECURITY: Session signing key.
# A random key generated per process breaks sessions and CSRF tokens between
# serverless instances, so production must provide a stable SECRET_KEY.
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    # Generate a temporary key so the module can always be imported (e.g. during
    # Vercel build-time analysis). In production this means sessions won't persist
    # across restarts — set SECRET_KEY as an environment variable to fix this.
    SECRET_KEY = os.urandom(24).hex()
    if not DEBUG_MODE:
        logger.warning(
            "SECRET_KEY is not set. A temporary key has been generated. "
            "Sessions and CSRF tokens will not persist across restarts. "
            "Set the SECRET_KEY environment variable in your host settings."
        )
    else:
        logger.warning("SECRET_KEY not set - using a temporary key (development only)")
app.config['SECRET_KEY'] = SECRET_KEY

# ✅ Gemini API configuration
def get_api_key():
    """Dynamically fetch and sanitize the Gemini API key.

    Production environment variables can contain surrounding quotes or whitespace.
    Checks explicit module-level `api_key` override first if set,
    then GEMINI_API_KEY / GOOGLE_API_KEY.
    """
    global api_key
    key = api_key if 'api_key' in globals() and api_key is not None else None
    if not key:
        key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        return None
    key = str(key).strip()
    if (key.startswith('"') and key.endswith('"')) or (key.startswith("'") and key.endswith("'")):
        key = key[1:-1].strip()
    return key if key else None



api_key = get_api_key()
if not api_key:
    logger.error("GEMINI_API_KEY or GOOGLE_API_KEY not set in environment variables")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
GEMINI_TIMEOUT_MS = int(os.getenv("GEMINI_TIMEOUT_MS", "30000"))

# ✅ YouTube video links for exercises
VIDEO_MAP = {
    "push-up": "https://www.youtube.com/embed/_l3ySVKYVJ8",
    "squat": "https://www.youtube.com/embed/aclHkVaku9U",
    "plank": "https://www.youtube.com/embed/pSHjTRCQxIw",
    "lunges": "https://www.youtube.com/embed/QOVaHwm-Q6U",
    "crunch": "https://www.youtube.com/embed/Xyd_fa5zoEU",
    "glute bridges": "https://www.youtube.com/embed/wPM8icPu6H8",
    "jump squats": "https://www.youtube.com/embed/U4s4mEQ5VqU",
    "sit-up": "https://www.youtube.com/embed/jDwoBqPH0jk",
    "bent-over dumbbell rows": "https://www.youtube.com/embed/vT2GjY_Umpw",
    "overhead press": "https://www.youtube.com/embed/qEwKCR5JCog",
    "dumbbell floor press": "https://www.youtube.com/embed/UixsWN8Gj5Y",
    "romanian deadlifts": "https://www.youtube.com/embed/0z6KAkzA3O4",
    "goblet squat": "https://www.youtube.com/embed/6xwGFn-J_QA"
}

# ✅ SECURITY: Allowed values for form fields
VALID_GOALS = ["fat loss", "muscle gain", "endurance", "general fitness"]
VALID_GENDERS = ["male", "female", "other"]
VALID_LEVELS = ["beginner", "intermediate", "advanced"]

# ✅ SECURITY: Input validation function
def validate_inputs(data):
    """Validate and sanitize user inputs"""
    errors = []
    
    # Validate goal
    if not data.get('goal') or data['goal'].lower() not in VALID_GOALS:
        errors.append("Invalid fitness goal")
    
    # Validate time
    try:
        time_val = int(data.get('time', 0))
        if time_val < 5 or time_val > 180:
            errors.append("Workout duration must be between 5 and 180 minutes")
    except (ValueError, TypeError):
        errors.append("Invalid workout duration")
    
    # Validate weight
    try:
        weight_val = float(data.get('weight', 0))
        if weight_val < 20 or weight_val > 300:
            errors.append("Weight must be between 20 and 300 kg")
    except (ValueError, TypeError):
        errors.append("Invalid weight")
    
    # Validate height
    try:
        height_val = int(data.get('height', 0))
        if height_val < 100 or height_val > 250:
            errors.append("Height must be between 100 and 250 cm")
    except (ValueError, TypeError):
        errors.append("Invalid height")
    
    # Validate age
    try:
        age_val = int(data.get('age', 0))
        if age_val < 13 or age_val > 120:
            errors.append("Age must be between 13 and 120 years")
    except (ValueError, TypeError):
        errors.append("Invalid age")
    
    # Validate gender
    if not data.get('gender') or data['gender'].lower() not in VALID_GENDERS:
        errors.append("Invalid gender selection")
    
    # Validate fitness level
    if not data.get('level') or data['level'].lower() not in VALID_LEVELS:
        errors.append("Invalid fitness level")
    
    return errors

# ✅ Custom error type: a failed Gemini call is reported, never silently swallowed
class GeminiError(RuntimeError):
    """Raised when the Gemini API call fails.

    ``kind`` is a short error code. ``title`` is a user-friendly category title.
    ``user_message`` is safe to show to the user without exposing secrets or tracebacks.
    """

    def __init__(self, kind, title, user_message=None):
        if user_message is None:
            # Handle 2-arg legacy call signature for backward compatibility in tests: GeminiError(kind, message)
            user_message = title
            title = "AI Service Error"
        super().__init__(kind)
        self.kind = kind
        self.title = title
        self.user_message = user_message


# ✅ Gemini client is created lazily and re-used across requests
_gemini_client = None
_last_client_key = None


def get_gemini_client():
    """Return the shared Gemini client, configured with a request timeout and current key."""
    global _gemini_client, _last_client_key
    current_key = get_api_key()
    if _gemini_client is None or _last_client_key != current_key:
        _gemini_client = genai.Client(
            api_key=current_key,
            http_options=genai_types.HttpOptions(timeout=GEMINI_TIMEOUT_MS)
        )
        _last_client_key = current_key
    return _gemini_client


def classify_gemini_error(error):
    """Map a Gemini SDK exception to (kind, title, user-safe message)."""
    code = getattr(error, "code", None) or getattr(error, "status_code", None)
    raw_msg = getattr(error, "message", str(error))
    details = f"{type(error).__name__} {code or ''} {raw_msg} {error}".lower()

    if (
        code in (401, 403)
        or "api key not valid" in details
        or "api_key" in details
        or "unauthenticated" in details
        or ("invalid" in details and "key" in details)
    ):
        return (
            "invalid_api_key",
            "API Key Authentication Error",
            "The Gemini API key is missing or invalid. Please check your production GEMINI_API_KEY environment variable."
        )
    if (
        code == 404
        or ("model" in details and ("not found" in details or "not supported" in details or "invalid" in details))
        or "not_found" in details
    ):
        return (
            "model_unavailable",
            "AI Model Unavailable",
            f"The model '{GEMINI_MODEL}' is unavailable or not supported for your API key. Try setting GEMINI_MODEL=gemini-3.5-flash or GEMINI_MODEL=gemini-flash-latest."
        )
    if (
        code == 429
        or "quota" in details
        or "resource_exhausted" in details
        or "rate limit" in details
    ):
        return (
            "quota_exceeded",
            "Quota / Rate Limit Exceeded",
            "The AI service is currently busy or rate-limited. Please wait a moment and try again."
        )
    if "timeout" in details or "timed out" in details:
        return (
            "timeout",
            "Request Timeout",
            "The AI took too long to generate a workout response. Please try again."
        )

    # Safe snippet for general API error
    user_msg = "Unable to generate workout due to an AI service error. Please try again later."
    if raw_msg and isinstance(raw_msg, str) and len(raw_msg) < 180 and not raw_msg.startswith("{"):
        key = get_api_key() or ""
        clean_msg = raw_msg.replace(key, "***") if key else raw_msg
        user_msg = f"AI API Error: {clean_msg}"

    return (
        "api_error",
        "AI Service Error",
        user_msg
    )



# ✅ Gemini query function with timeout and error handling
def query_gemini(prompt):
    """Query Gemini API with a timeout; raises GeminiError on failure."""
    current_key = get_api_key()
    if not current_key:
        logger.error("Cannot query Gemini: GEMINI_API_KEY is not set")
        raise GeminiError(
            "not_configured",
            "API Key Missing",
            "The workout service is not configured with a valid GEMINI_API_KEY environment variable."
        )

    try:
        client = get_gemini_client()
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )
    except Exception as e:
        logger.exception("Gemini request failed for model %s", GEMINI_MODEL)
        kind, title, user_message = classify_gemini_error(e)
        raise GeminiError(kind, title, user_message) from e

    text = getattr(response, "text", None)
    if not text or not text.strip():
        logger.error("Gemini returned an empty response for model %s", GEMINI_MODEL)
        raise GeminiError(
            "empty_response",
            "Empty AI Response",
            "The AI could not produce a workout plan. Please try again."
        )

    logger.info("Successfully generated workout plan")
    return text.strip()

# ✅ SECURITY: Add security headers
@app.after_request
def set_security_headers(response):
    """Add security headers to all responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-eval' 'unsafe-inline' https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "frame-src https://www.youtube.com; "
        "img-src 'self' data: blob:; "
        "connect-src 'self' https://cdnjs.cloudflare.com"
    )
    return response

@app.route('/healthz')
@limiter.exempt
def healthz():
    """Lightweight health probe - never exposes the API key itself."""
    current_key = get_api_key()
    return jsonify(
        status="ok",
        gemini_key_configured=bool(current_key),
        gemini_model=GEMINI_MODEL,
    )


@app.route('/')
def index():
    return render_template("index.html")

@app.route('/generate', methods=['POST'])
@limiter.limit("10 per minute")  # Rate limit: 10 requests per minute
def generate():
    """Generate personalized workout plan"""
    try:
        # Validate inputs
        validation_errors = validate_inputs(request.form)
        if validation_errors:
            logger.warning(f"Invalid input: {validation_errors}")
            return render_template(
                "index.html",
                validation_errors=validation_errors,
                errors=validation_errors,
                form_data=request.form
            ), 400
        
        # Extract and sanitize form data
        goal = bleach.clean(request.form['goal'])
        time = int(request.form['time'])
        equipment = bleach.clean(request.form.get('equipment', '').strip())
        weight = float(request.form['weight'])
        height = int(request.form['height'])
        age = int(request.form['age'])
        gender = bleach.clean(request.form['gender'])
        level = bleach.clean(request.form['level'])

        # Build prompt
        prompt = (
            f"Generate a {time}-minute personalized workout plan for the goal: {goal}. "
            f"User details: {gender}, {age} years old, {weight}kg, {height}cm tall, "
            f"fitness level: {level}. Use {equipment if equipment else 'no equipment'}."
        )

        # Query Gemini API (upstream failures surface as 503, not as a silent 500)
        try:
            response_text = query_gemini(prompt)
        except GeminiError as e:
            logger.error("Workout generation failed: %s (%s)", e.kind, e.title)
            api_error_obj = {
                "kind": e.kind,
                "title": e.title,
                "message": e.user_message
            }
            return render_template(
                "index.html",
                api_error=api_error_obj,
                errors=[e.user_message],
                form_data=request.form
            ), 503

        # ✅ SECURITY: Convert markdown to HTML and sanitize output
        html_workout = bleach.clean(
            markdown.markdown(response_text),
            tags=['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'br', 'strong', 'em', 'u'],
            strip=True
        )

        # Match exercise videos
        matched_videos = []
        for key in VIDEO_MAP:
            if re.search(rf'\b{key}\b', response_text, re.IGNORECASE):
                matched_videos.append((key.title(), VIDEO_MAP[key]))

        logger.info("Workout plan generated successfully")
        return render_template("result.html", workout=html_workout, videos=matched_videos)


# ✅ Server-side PDF generation endpoint
@app.route('/download_pdf', methods=['POST'])
@limiter.limit("5 per minute")
def download_pdf():
    """Generate a PDF from the provided workout HTML and send as download."""
    workout_html = request.form.get('workout_html')
    if not workout_html:
        logger.error("No workout_html provided for PDF generation")
        return jsonify({"error": "No workout data supplied"}), 400
    try:
        # Convert the HTML string to PDF using WeasyPrint
        pdf_bytes = HTML(string=workout_html).write_pdf()
        pdf_io = BytesIO(pdf_bytes)
        pdf_io.seek(0)
        return send_file(
            pdf_io,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='Workout_Plan.pdf'
        )
    except Exception as e:
        logger.exception("PDF generation failed")
        return jsonify({"error": "Failed to generate PDF"}), 500
    
    except Exception:
        logger.exception("Unexpected error in /generate")
        api_error_obj = {
            "kind": "unexpected",
            "title": "Unexpected Server Error",
            "message": "An unexpected system error occurred. Please try again."
        }
        return render_template(
            "index.html",
            api_error=api_error_obj,
            errors=["An unexpected error occurred. Please try again."],
            form_data=request.form
        ), 500

if __name__ == '__main__':
    # ✅ SECURITY: Use environment variable for debug mode
    app.run(debug=DEBUG_MODE, host='0.0.0.0', port=5000)
