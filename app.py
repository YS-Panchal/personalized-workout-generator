from flask import Flask, render_template, request
import google.generativeai as genai
import markdown
import re
import os
from dotenv import load_dotenv
load_dotenv()


app = Flask(__name__)

# ✅ Configure Gemini API (Replace with your actual key)
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


# ✅ YouTube video links for exercises
video_map = {
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

# ✅ Gemini query function
def query_gemini(prompt):
    try:
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print("❌ Inference error:", e)
        return "<p class='error-msg'>Sorry, something went wrong. Please try again later.</p>"

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/generate', methods=['POST'])
def generate():
    goal = request.form['goal']
    time = request.form['time']
    equipment = request.form['equipment']
    weight = request.form['weight']
    height = request.form['height']
    age = request.form['age']
    gender = request.form['gender']
    level = request.form['level']

    prompt = (
        f"Generate a {time}-minute personalized workout plan for the goal: {goal}. "
        f"User details: {gender}, {age} years old, {weight}kg, {height}cm tall, "
        f"fitness level: {level}. Use {equipment if equipment else 'no equipment'}."
    )

    response_text = query_gemini(prompt)
    html_workout = markdown.markdown(response_text)

    matched_videos = []
    for key in video_map:
            if re.search(rf'\b{key}\b', response_text, re.IGNORECASE):
                matched_videos.append((key.title(), video_map[key]))

            return render_template("result.html", workout=html_workout, videos=matched_videos)

if __name__ == '__main__':
    app.run(debug=True)
