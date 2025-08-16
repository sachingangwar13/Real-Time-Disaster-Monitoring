import streamlit as st
import firebase_admin
from firebase_admin import credentials, auth, exceptions
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
# Initialize Firebase Admin SDK
cred = credentials.Certificate(os.getenv('FIREBASE_CREDENTIALS_JSON'))
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)


def send_email(email):
    """Send a welcome email to the user."""
    email_sender = os.getenv('EMAIL')
    email_password = os.getenv('PASSWORD')
    email_receiver = email
    subject = "Welcome to Real-Time Disaster Monitoring"

    # Email content
    msg = MIMEMultipart("alternative")
    msg["From"] = email_sender
    msg["To"] = email_receiver
    msg["Subject"] = subject

    html_content = f"""
    <html>
    <body>
        <p>Dear User,</p>
        <p>Welcome to Real-Time Disaster Monitoring! We're excited to have you on board.</p>
        <p>Explore and monitor disaster events in real-time with advanced features like interactive maps, analytics, and more!</p>
        <p>Best regards,<br>Sachin Gangwar</p>
    </body>
    </html>
    """
    msg.attach(MIMEText(html_content, "html"))

    # Send the email
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as smtp:
        smtp.login(email_sender, email_password)
        smtp.sendmail(email_sender, email_receiver, msg.as_string())


def main():
    st.title(":green[Real Time Disaster Information Aggregation Software]")

    # Initialize session state variables
    if "username" not in st.session_state:
        st.session_state["username"] = ""
    if "useremail" not in st.session_state:
        st.session_state["useremail"] = ""
    if "signedout" not in st.session_state:
        st.session_state["signedout"] = False
    if "signout" not in st.session_state:
        st.session_state["signout"] = False

    # Signup logic
    def sign_up(email, password, username):
        if len(password) < 6:
            st.error("Password must be at least 6 characters long.")
            return

        try:
            # Check if the email is already registered
            auth.get_user_by_email(email)
            st.error("This email is already in use. Please use a different email.")
            return

        except exceptions.NotFoundError:
            # If the email is not registered, proceed with signup
            try:
                # Create a new user
                user = auth.create_user(email=email, password=password, uid=username)
                st.success("Account created successfully! Check your email for details.")
                st.balloons()
                send_email(email)
            except Exception as e:
                st.error(f"Failed to create account: {str(e)}")

    # Login logic
    def login(email, password):
        try:
            user = auth.get_user_by_email(email)
            st.success("Login Successful")
            st.session_state["username"] = user.uid
            st.session_state["useremail"] = user.email
            st.session_state["signedout"] = True
            st.session_state["signout"] = True
        except exceptions.NotFoundError:
            st.error("Invalid email or password.")
        except Exception as e:
            st.error(f"Login failed: {str(e)}")

    # Sign out logic
    def sign_out():
        st.session_state["signout"] = False
        st.session_state["signedout"] = False
        st.session_state["username"] = ""
        st.session_state["useremail"] = ""

    if not st.session_state["signedout"]:
        choice = st.radio("Login or Signup", ["Login", "Sign Up"])

        if choice == "Login":
            email = st.text_input("Email Address")
            password = st.text_input("Password", type="password")
            if st.button("Login"):
                login(email, password)

        elif choice == "Sign Up":
            email = st.text_input("Email Address")
            password = st.text_input("Password", type="password")
            username = st.text_input("Username")
            if st.button("Create my account"):
                sign_up(email, password, username)

    if st.session_state["signout"]:
        st.text(f"Name: {st.session_state['username']}")
        st.text(f"Email ID: {st.session_state['useremail']}")
        if st.button("Sign out"):
            sign_out()


if __name__ == "__main__":
    main()
