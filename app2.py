import os
import streamlit as st
import requests
import pandas as pd

# Check for required libraries
try:
    import dotenv
    DOTENV_INSTALLED = True
except ImportError:
    DOTENV_INSTALLED = False
    st.error("python-dotenv library is not installed. Please install it using 'pip install python-dotenv'")

try:
    import resend
    RESEND_INSTALLED = True
except ImportError:
    RESEND_INSTALLED = False
    st.error("Resend library is not installed. Please install it using 'pip install resend'")
    st.info("You can still use the email generator, but sending emails will be disabled.")

if not DOTENV_INSTALLED:
    st.stop()

# Load environment variables
dotenv.load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")

# Check if API keys are set
if not GROQ_API_KEY:
    st.error("GROQ_API_KEY is not set in the .env file")
    st.stop()

if RESEND_INSTALLED and not RESEND_API_KEY:
    st.warning("RESEND_API_KEY is not set in the .env file. Email sending will be disabled.")

# API Configuration
LLM_URL = "https://api.groq.com/openai/v1/chat/completions"
LLM_HEADERS = {"Authorization": f"Bearer {GROQ_API_KEY}"}

if RESEND_INSTALLED and RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": (
            "You are an AI assistant generating personalized emails. "
            "Use the provided information to create customized email content."
        )}
    ]
    st.session_state.email_generated = False
    st.session_state.profile = {}

# Helper function to call Groq Cloud LLM API
def get_llm_response(messages):
    body = {"model": "llama3-8b-8192", "messages": messages}
    response = requests.post(LLM_URL, headers=LLM_HEADERS, json=body)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        st.error(f"API request failed with status code {response.status_code}")
        st.stop()

# Helper function to send email via Resend
def send_email(subject, body, recipient_email):
    if not RESEND_INSTALLED or not RESEND_API_KEY:
        st.error("Email sending is not available. Please install Resend and set the API key.")
        return None
    
    try:
        params: resend.Emails.SendParams = {
            "from": "onboarding@resend.dev",
            "to": [recipient_email],
            "subject": subject,
            "html": body,
        }
        email: resend.Email = resend.Emails.send(params)
        return email
    except Exception as e:
        st.error(f"Failed to send email: {str(e)}")
        return None

# User Profile Setup and Storage
def save_profile(profile):
    df = pd.DataFrame([profile])
    df.to_csv("user_profiles.csv", mode='a', index=False, header=False)

def load_profiles():
    try:
        return pd.read_csv("user_profiles.csv", names=["Name", "Industry", "Company", "Target Audience"])
    except FileNotFoundError:
        return pd.DataFrame(columns=["Name", "Industry", "Company", "Target Audience"])

# Streamlit UI Setup
st.title("EmailGenie - Personalized Email Generator")

# Step 1: User Profile Setup
st.header("Step 1: User Profile Setup")

profile_choice = st.radio("Choose an option", ["Load Existing Profile", "Create New Profile"])

if profile_choice == "Load Existing Profile":
    profiles = load_profiles()
    if not profiles.empty:
        profile_names = profiles["Name"].tolist()
        selected_profile = st.selectbox("Select a profile", profile_names)
        st.session_state.profile = profiles[profiles["Name"] == selected_profile].iloc[0].to_dict()
    else:
        st.warning("No existing profiles found. Please create a new profile.")
        profile_choice = "Create New Profile"

if profile_choice == "Create New Profile":
    st.session_state.profile = {}

name = st.text_input("Your Name", value=st.session_state.profile.get("Name", ""))
industry = st.text_input("Industry", value=st.session_state.profile.get("Industry", ""))
company = st.text_input("Company (Optional)", value=st.session_state.profile.get("Company", ""))
audience = st.text_area("Target Audience Description", value=st.session_state.profile.get("Target Audience", ""))

if st.button("Save Profile"):
    profile = {"Name": name, "Industry": industry, "Company": company, "Target Audience": audience}
    save_profile(profile)
    st.session_state.profile = profile
    st.success("Profile saved successfully!")

# Step 2: Email Parameters
st.header("Step 2: Email Parameters")
recipient_name = st.text_input("Recipient's Name")
recipient_email = st.text_input("Recipient's Email as using Resend API can only use my email id like spam.vanshjain@gmail.com")
email_purpose = st.text_input("Email Purpose (e.g., Job Application, Sales Pitch, Follow-up)")
tone = st.select_slider("Tone", options=["Formal", "Neutral", "Friendly"], value="Neutral")
length = st.select_slider("Length", options=["Short", "Medium", "Long"], value="Medium")
key_points = st.text_area("Key Points to Include")

# Step 3: Generate Email
st.header("Step 3: Generate Email")
if st.button("Generate Email"):
    prompt = f"""
    Generate a personalized email based on the following information:
    - Sender: {name} from {company} in the {industry} industry
    - Recipient: {recipient_name}
    - Purpose: {email_purpose}
    - Tone: {tone}
    - Length: {length}
    - Key Points: {key_points}
    - Target Audience: {audience}

    Please create an email that addresses the recipient by name, clearly states the purpose,
    maintains the specified tone and length, and incorporates the key points provided. And do not include any AI or AI generated text like (Here is a personalized email that addresses your needs ) nothing like that. and also do not include any placeholder text. and do not repeat the subject line in the email body.
    """
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    response = get_llm_response(st.session_state.messages)
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.session_state.email_generated = True

    st.subheader("Generated Email:")
    st.text_area("Email Content", response, height=300)

# Step 4: Preview and Send Email
if st.session_state.email_generated:
    st.header("Step 4: Preview & Send Email")
    email_subject = st.text_input("Email Subject", value=f"{email_purpose} - {recipient_name}")
    
    if st.button("Send Email"):
        if RESEND_INSTALLED and RESEND_API_KEY:
            recipient_email = "spam.vanshjain@gmail.com"; # Fixed email address
            email_result = send_email(email_subject, st.session_state.messages[-1]["content"], recipient_email)
            # Check if email_result is a dictionary and contains 'id'
            if email_result is None:
                st.error("Failed to send email: email_result is None.")
            elif isinstance(email_result, dict) and 'id' in email_result:
                st.success(f"Email sent successfully! Email ID: {email_result['id']}")
            else:
                st.error(f"Failed to send email: email_result does not have an 'id'. Received: {email_result}")
        else:
            st.error("Email sending is not available. Please install Resend and set the API key.")

# Optional: View Conversation History
with st.expander("Conversation History", expanded=False):
    for message in st.session_state.messages[1:]:
        if message["role"] == "assistant":
            st.write(f"**AI:** {message['content']}")
        elif message["role"] == "user":
            st.write(f"**You:** {message['content']}")

# Optional: Start Over Button
if st.button("Start Over"):
    st.session_state.messages = [
        {"role": "system", "content": (
            "You are an AI assistant generating personalized emails. "
            "Use the provided information to create customized email content."
        )}
    ]
    st.session_state.email_generated = False
    st.session_state.profile = {}
    st.rerun()
