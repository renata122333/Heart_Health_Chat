from flask import Flask, render_template, redirect, url_for, request, session, flash, jsonify
from firebase_init import initialize_firebase
import firebase_admin
from firebase_admin import auth
import google.auth.exceptions
from datetime import timedelta

# Initialize Flask application
app = Flask(__name__)

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=60)
app.secret_key = 'your-secret-key'
# Set a secret key for session management

# Import and register chatbot blueprint
from chatbot import chatbot_routes

app.register_blueprint(chatbot_routes, url_prefix='/chatbot')

# Initialize Firebase
initialize_firebase()


# Verify ID Token and set session
@app.route('/verify_token', methods=['POST'])
def verify_token():
    token = request.json.get('token')

    try:
        # Verify the token using Firebase Admin SDK
        decoded_token = auth.verify_id_token(token)
        user_uid = decoded_token['uid']

        # Set the user ID in the session
        session['user'] = user_uid
        return jsonify({'success': True})
    except Exception as e:
        print(f"Token verification failed: {e}")
        return jsonify({'success': False})


# Route for signup page
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        try:
            # Create a new user with Firebase
            user = auth.create_user(
                email=email,
                password=password,
                display_name=name
            )
            flash('Signup successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except firebase_admin.exceptions.FirebaseError as e:
            flash(f'Signup failed: {e}', 'error')

    return render_template('signup.html')


# Route for login page
@app.route('/', methods=['GET', 'POST'])
def login():
    return render_template('login.html')


# Home page route (protected)
@app.route('/home')
def home():
    if 'user' not in session:
        # User is not logged in, redirect to login page
        return redirect(url_for('login'))
    return render_template('home.html')

# Profile page route
@app.route('/profile_page')
def profile_page():
    user = {
        #test user for profile page rendering
        'name': 'John',
        'surname': 'Doe',
        'dob': '01/01/1990',
        'email': 'john.doe@example.com',
        'description': 'This is a sample description.',
        'profile_picture_url': 'https://placehold.co/100x100'
    }
    return render_template('profile_page.html',  user=user)

# Logout route
@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
