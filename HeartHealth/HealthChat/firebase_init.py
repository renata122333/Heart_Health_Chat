import firebase_admin
from firebase_admin import credentials, auth

# Flag to check if Firebase has already been initialized
firebase_initialized = False

def initialize_firebase():
    if not firebase_admin._apps:
        try:
            cred = credentials.Certificate('path/to/service_key.json')  # Replace with the path to your service key
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://heartchat-7268c-default-rtdb.firebaseio.com/'
            })
            print("Firebase successfully initialized.")
        except Exception as e:
            print(f"Failed to initialize Firebase: {e}")
