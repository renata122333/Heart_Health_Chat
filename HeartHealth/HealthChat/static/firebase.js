import { initializeApp } from "https://www.gstatic.com/firebasejs/9.16.0/firebase-app.js";
import { getAuth, signInWithEmailAndPassword, createUserWithEmailAndPassword } from "https://www.gstatic.com/firebasejs/9.16.0/firebase-auth.js";

// Your web app's Firebase configuration
  const firebaseConfig = {
    apiKey: "AIzaSyATBSNccQUICwXJL-3hR5LdSVoLAX513N4",
    authDomain: "heartchat-7268c.firebaseapp.com",
    projectId: "heartchat-7268c",
    storageBucket: "heartchat-7268c.appspot.com",
    messagingSenderId: "55342640146",
    appId: "1:55342640146:web:94f93184b34e2bfb2c3ccb"
  };

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

// Login Function
window.login = () => {
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    signInWithEmailAndPassword(auth, email, password)
        .then(async (userCredential) => {
            // Signed in
            const user = userCredential.user;

            // Get ID token
            const idToken = await user.getIdToken();

            // Send the ID token to the server
            fetch('/verify_token', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ token: idToken })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Login successful!');
                    window.location.href = '/home';  // Redirect to home page
                } else {
                    alert('Login failed. Please try again.');
                }
            });
        })
        .catch((error) => {
            alert(error.message);
        });
};



// Signup Function
window.signup = () => {
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    createUserWithEmailAndPassword(auth, email, password)
        .then((userCredential) => {
            // Signed up
            const user = userCredential.user;
            alert('Signup successful!');
            window.location.href = '/';  // Redirect to login page
        })
        .catch((error) => {
            alert(error.message);
        });
};
