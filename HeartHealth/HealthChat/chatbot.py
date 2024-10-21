from firebase_admin import auth
from flask import Blueprint, request, render_template, session, g, url_for, flash, redirect
from model import make_prediction as model_prediction, numerical_features, categorical_features, firebase_ref
import google.generativeai as genai
from datetime import datetime

chatbot_routes = Blueprint('chatbot_routes', __name__)

questions = [
    {"question": "What is your age? (18-100)", "range": "18-120"},
    {"question": "What is your cholesterol level? (100-300 mg/dL)", "range": "100-300"},
    {"question": "What is your systolic blood pressure? (90-180 mmHg)", "range": "90-180"},
    {"question": "What is your diastolic blood pressure? (60-120 mmHg)", "range": "60-120"},
    {"question": "What is your heart rate? (60-100 bpm)", "range": "60-100"},
    {"question": "What is your BMI? (15-40)", "range": "15-40"},
    {"question": "What is your triglycerides level? (50-500 mg/dL)", "range": "50-500"},
    {"question": "How many hours per week do you exercise? (0-30)", "range": "0-30"},
    {"question": "How many days per week are you physically active? (0-7)", "range": "0-7"},
    {"question": "How many hours do you sleep per day? (4-12)", "range": "4-12"},
    {"question": "How many hours per day do you spend being sedentary? (0-24)", "range": "0-24"},
    {"question": "What is your sex? (Male/Female)", "range": "Male/Female"},
    {"question": "Do you have diabetes? (Yes/No)", "range": "Yes/No"},
    {"question": "Do you have a family history of heart disease? (Yes/No)", "range": "Yes/No"},
    {"question": "Do you smoke? (Yes/No)", "range": "Yes/No"},
    {"question": "Are you obese? (Yes/No)", "range": "Yes/No"},
    {"question": "Do you consume alcohol? (Yes/No)", "range": "Yes/No"},
    {"question": "How would you describe your diet? (Healthy/Unhealthy)", "range": "Healthy/Unhealthy"},
    {"question": "Have you had any previous heart problems? (Yes/No)", "range": "Yes/No"},
    {"question": "Do you take any medication regularly? (Yes/No)", "range": "Yes/No"},
    {"question": "On a scale of 1-5, how would you rate your stress level? (1-5)", "range": "1-5"},
    {"question": "What is your income level? (Low/Medium/High)", "range": "Low/Medium/High"}
]

# Configure Generative AI
genai.configure(api_key="AIzaSyAd0kEzSrkQ6fT4qGqyRxDY0CWolic7_N0")
model = genai.GenerativeModel('gemini-pro')


@chatbot_routes.route('/', methods=['GET', 'POST'])
def index():
    user_name = "Anonymous"
    user_id = None
    if 'user' not in session:
        flash('Please log in to access the chatbot.', 'error')
        return redirect(url_for('login'))

    try:
        # Get user information from Firebase
        user = auth.get_user(session['user'])
        user_name = user.display_name or "Anonymous"
        user_id = user.uid
    except Exception as e:
        print(f"Error retrieving user data: {e}")

    if 'chat_messages' not in session:
        session['chat_messages'] = []
        session['current_question'] = 0
        session['user_responses'] = {"What is your name?": user_name}
        session['chat_messages'].append(
            {"content": f"Hello {user_name}! Let's start your heart health assessment.", "is_user": False})
        session['chat_messages'].append({"content": questions[0]['question'], "is_user": False})

    if request.method == 'POST':
        user_message = request.form.get('message')
        print(f"Received user message: {user_message}")  # Debug log

        current_question = session['current_question']
        if current_question < len(questions):
            if validate_input(questions[current_question], user_message):
                session['user_responses'][questions[current_question]['question']] = user_message
                session['chat_messages'].append({"content": user_message, "is_user": True})
                session['current_question'] += 1

                if session['current_question'] < len(questions):
                    bot_message = questions[session['current_question']]['question']
                else:
                    print(f"All questions answered. User responses: {session['user_responses']}")  # Debug log
                    risk, advice = make_prediction(session['user_responses'])
                    if risk == "Error":
                        risk, advice = gemini_prediction(session['user_responses'])

                    bot_message = f"Based on your responses, your risk of heart disease is {risk}.<br><br>Advice:<br>{advice}"
                    if user_id and risk != "Unable to assess" and risk != "Error":
                        store_assessment(user_id, session['user_responses'], risk, advice)

                session['chat_messages'].append({"content": bot_message, "is_user": False})
            else:
                error_message = f"Invalid input. Please check the range: {questions[current_question]['range']}"
                session['chat_messages'].append({"content": error_message, "is_user": False})

        session.modified = True

    history = get_user_history(user_id) if user_id else []
    return render_template('index.html', chat_messages=session['chat_messages'], history=history, user_name=user_name)

def make_prediction(responses):
    try:
        # Prepare the responses for the model
        model_responses = {}
        for feature in numerical_features + categorical_features:
            question = next((q['question'] for q in questions if feature in q['question']), None)
            if question and question in responses:
                model_responses[feature] = responses[question]
            else:
                print(f"Missing response for feature: {feature}")
                return "Error", "Missing some required information for prediction."

        # Call the model's prediction function
        risk, advice = model_prediction(model_responses)
        return risk, advice
    except Exception as e:
        print(f"Error in make_prediction: {e}")
        return "Error", "There was an issue processing your data."
def validate_input(question, response):
    if question['range'] == "Text":
        return True
    elif '/' in question['range']:
        valid_options = [option.lower() for option in question['range'].split('/')]
        return response.lower() in valid_options
    elif '-' in question['range']:
        min_val, max_val = map(float, question['range'].split('-'))
        try:
            value = float(response)
            return min_val <= value <= max_val
        except ValueError:
            return False
    return False


import re


def clean_text(text):
    # Remove asterisks and other symbols, but keep structure
    cleaned = re.sub(r'\*+', '', text)
    cleaned = re.sub(r'["""]', '', cleaned)
    # Replace multiple newlines with a single newline
    cleaned = re.sub(r'\n+', '\n', cleaned)
    # Remove leading/trailing whitespace from each line
    cleaned = '\n'.join(line.strip() for line in cleaned.split('\n'))
    return cleaned


def gemini_prediction(responses):
    prompt = f"Based on the following health data, assess the risk of heart disease and provide advice: {responses}"
    try:
        response = model.generate_content(prompt)

        if response.candidates and response.candidates[0].content:
            text = response.candidates[0].content.parts[0].text
            risk = "moderate"  # Default risk
            if "high risk" in text.lower():
                risk = "high"
            elif "low risk" in text.lower():
                risk = "low"

            # Clean the advice text
            cleaned_advice = clean_text(text)

            return risk, cleaned_advice
        else:
            return "Unable to assess", "I apologize, but I couldn't generate a specific assessment based on the provided information. Please consult with a healthcare professional for accurate health advice."
    except ValueError as e:
        print(f"Error in Gemini prediction: {e}")
        return "Error", "I encountered an error while processing your information. Please try again or consult with a healthcare professional for accurate health advice."


def store_assessment(user_id, responses, risk, advice):
    try:
        user_ref = firebase_ref.child(user_id)
        new_assessment = {
            "responses": responses,
            "risk": risk,
            "advice": advice,
            "timestamp": datetime.now().timestamp()
        }
        user_ref.push(new_assessment)
    except Exception as e:
        print(f"Error storing assessment: {e}")


def get_user_history(user_id):
    try:
        user_ref = firebase_ref.child(user_id)
        history = user_ref.get()
        if history:
            formatted_history = []
            for key, record in history.items():
                formatted_history.append({
                    "timestamp": datetime.fromtimestamp(record['timestamp']).strftime('%Y-%m-%d %H:%M:%S'),
                    "question": "Health Assessment",
                    "risk": record['risk'],
                    "advice": record['advice']
                })
            return formatted_history
        else:
            return []
    except Exception as e:
        print(f"Error retrieving user history: {e}")
        return []


@chatbot_routes.route('/new_chat', methods=['POST'])
def new_chat():
    session.pop('chat_messages', None)
    session.pop('current_question', None)
    session.pop('user_responses', None)
    return redirect(url_for('chatbot_routes.index'))
