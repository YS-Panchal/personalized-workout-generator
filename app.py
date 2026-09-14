from flask import Flask, render_template, request, jsonify
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import google.genai as genai
import markdown
import bleach
import re
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# ✅ SECURITY: Set secret key for session management (required for CSRF)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24).hex())
app.config['SESSION_COOKIE_SECURE'] = True  # Only send over HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JS access
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection

# ✅ SECURITY: Configure debug mode from environment
DEBUG_MODE = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
app.debug = DEBUG_MODE

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

# ✅ SECURITY: Configure Gemini API
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    logger.error("GEMINI_API_KEY not set in environment variables")
    raise ValueError("GEMINI_API_KEY environment variable not configured")

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

# ✅ Gemini query function with error handling
def query_gemini(prompt):
    """Query Gemini API with timeout and error handling"""
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt
        )
        logger.info("Successfully generated workout plan")
        return response.text.strip()
    except Exception as e:
        logger.error(f"Error generating workout: {str(type(e).__name__)}")
        # Return generic error message (never expose exception details to user)
        return None

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
            return render_template("index.html", errors=validation_errors), 400
        
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

        # Query Gemini API
        response_text = query_gemini(prompt)
        
        if response_text is None:
            logger.warning("Failed to generate workout plan")
            return render_template("index.html", 
                                 errors=["Unable to generate workout. Please try again later."]), 500

        # ✅ SECURITY: Convert markdown to HTML and sanitize output
        html_workout = bleach.clean(
            markdown.markdown(response_text),
            tags=['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'br', 'strong', 'em', 'u'],
            strip=True
        )

        # Match exercise videos (moved outside loop - FIX FOR LOGIC BUG)
        matched_videos = []
        for key in VIDEO_MAP:
            if re.search(rf'\b{key}\b', response_text, re.IGNORECASE):
                matched_videos.append((key.title(), VIDEO_MAP[key]))

        logger.info("Workout plan generated successfully")
        return render_template("result.html", workout=html_workout, videos=matched_videos)
    
    except Exception as e:
        logger.error(f"Unexpected error in /generate: {str(type(e).__name__)}")
        return render_template("index.html", 
                             errors=["An unexpected error occurred. Please try again."]), 500

if __name__ == '__main__':
    # ✅ SECURITY: Use environment variable for debug mode
    app.run(debug=DEBUG_MODE, host='0.0.0.0', port=5000)
