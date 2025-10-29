import os
import pandas as pd
import streamlit as st
import smtplib
from email.mime.text import MIMEText
from itertools import cycle
import time
import requests

st.set_page_config(page_title="💬 Communication Hub", page_icon="💎", layout="centered")

# ============= Helper: Dynamic paths =============
# إذا التطبيق يشتغل على جهازك المحلي (Windows)
LOCAL_RECEIVERS = r"C:\Users\Ban\OneDrive\Desktop\communication sys\emails.csv"
LOCAL_SENDERS = r"C:\Users\Ban\OneDrive\Desktop\communication sys\senders-emails.csv"

# أما لو يشتغل على Streamlit Cloud أو تم رفع الملفات داخل مجلد data
CLOUD_RECEIVERS = "./data/emails.csv"
CLOUD_SENDERS = "./data/senders-emails.csv"

def get_file_path(local_path, cloud_path):
    """يرجع المسار المناسب حسب المكان اللي يشغَّل منه"""
    if os.path.exists(local_path):
        return local_path
    elif os.path.exists(cloud_path):
        return cloud_path
    else:
        st.error(f"❌ الملف مش موجود لا محليًا ولا داخل data/: {cloud_path}")
        st.stop()

RECEIVERS_PATH = get_file_path(LOCAL_RECEIVERS, CLOUD_RECEIVERS)
SENDERS_PATH = get_file_path(LOCAL_SENDERS, CLOUD_SENDERS)

# ============= API Class =============
def get_secret(key):
    try:
        val = st.secrets.get(key)
        if val:
            return val
    except Exception:
        pass
    return os.environ.get(key)

class EvolutionAPI:
    def __init__(self):
        self.BASE_URL = get_secret("EVO_BASE_URL") or "http://localhost:8080"
        self.INSTANCE_NAME = get_secret("EVO_INSTANCE_NAME") or "test"
        self.__api_key = get_secret("AUTHENTICATION_API_KEY") or ""
        self.__headers = {"apikey": self.__api_key, "Content-Type": "application/json"}

    def send_message(self, number, text):
        payload = {"number": str(number).strip(), "text": text}
        try:
            response = requests.post(
                url=f"{self.BASE_URL}/message/sendText/{self.INSTANCE_NAME}",
                headers=self.__headers,
                json=payload,
                timeout=15
            )
            res_json = response.json()
        except requests.exceptions.RequestException as e:
            res_json = {"error": "request_exception", "detail": str(e)}
        except Exception:
            res_json = {"error": "Invalid JSON response"}
        print("📩 API Response:", res_json)
        return res_json

# ============= UI =============
st.markdown("<h1>💬 Communication Hub</h1>", unsafe_allow_html=True)
st.write("Send your messages professionally via Email or WhatsApp 🚀")

try:
    receivers_df = pd.read_csv(RECEIVERS_PATH)
    senders_df = pd.read_csv(SENDERS_PATH)
    st.success(f"✅ Receivers loaded: **{len(receivers_df)}** | Senders loaded: **{len(senders_df)}**")
except Exception as e:
    st.error(f"❌ Error loading CSV files: {e}")
    st.stop()

method = st.selectbox("📤 Choose Sending Method", ["Email", "WhatsApp"])
delay = st.number_input("⏱️ Delay between messages (seconds)", min_value=0.0, value=2.0, step=0.5)

if method == "Email":
    subject = st.text_input("📌 Email Subject", "Test Email")
    body_template = st.text_area("💌 Email Body", "Hello {name},\nThis is a test email from my project!")
else:
    body_template = st.text_area("💬 WhatsApp Message", "Hi {name}, this is a test WhatsApp message!")
    subject = None

if "dept" in receivers_df.columns:
    departments = sorted(receivers_df["dept"].dropna().unique().tolist())
    selected_depts = st.multiselect("🏢 Choose Department(s)", options=departments, default=departments)
    filtered_df = receivers_df if not selected_depts else receivers_df[receivers_df["dept"].isin(selected_depts)]
else:
    filtered_df = receivers_df

st.divider()
st.subheader("🚀 Ready to Send")

if st.button(f"Send {method} Messages Now"):
    st.success("✨ Sending started instantly!", icon="⚡")
    total = len(filtered_df)
    sent_count = 0
    senders_cycle = cycle(senders_df.to_dict(orient="records"))
    api = EvolutionAPI()

    for _, row in filtered_df.iterrows():
        name = row.get("name", "there")
        message = body_template.format(name=name)
        try:
            if method == "Email":
                sender_data = next(senders_cycle)
                sender_email = sender_data.get("email")
                app_password = sender_data.get("app_password")
                receiver = row.get("email")

                msg = MIMEText(message)
                msg["Subject"] = subject
                msg["From"] = sender_email
                msg["To"] = receiver

                server = smtplib.SMTP("smtp.gmail.com", 587)
                server.starttls()
                server.login(sender_email, app_password)
                server.send_message(msg)
                server.quit()
            else:
                number = str(row["number"]).strip()
                api.send_message(number, message)
            sent_count += 1
        except Exception as e:
            st.error(f"❌ Failed for {name}: {e}")
        time.sleep(float(delay))

    st.success(f"🎉 Done! {sent_count}/{total} messages sent successfully.", icon="✅")
