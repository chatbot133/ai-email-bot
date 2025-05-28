import imaplib
import smtplib
import email
from email.message import EmailMessage
from email.utils import parseaddr
import time
import requests
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv
load_dotenv()
from flask import Flask
import threading

EMAIL = os.environ["EMAIL_ADDRESS"]
PASSWORD = os.environ["APP_PASSWORD"]
API_KEY = os.environ["OPENROUTER_API_KEY"]
MODEL = os.environ["MODEL"]



def get_ai_response(prompt):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "HTTP-Referer": "https://you.com",
        "X-Title": "EmailBot"
    }
    data = {
        "model": MODEL,
        "messages": [{
            "role": "user",
            "content": prompt
        }],
        "max_tokens": 500  # updated to give longer replies
    }

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            json=data,
            headers=headers)

        print("\n📡 RAW STATUS:", response.status_code)
        print("📦 RAW TEXT:", response.text)

        response.raise_for_status()
        response_json = response.json()

        if "choices" not in response_json or not response_json["choices"]:
            return f"⚠️ No 'choices' in response. Full response: {response_json}"

        return response_json["choices"][0]["message"]["content"]

    except Exception as e:
        print("❌ Error contacting OpenRouter:", str(e))
        return "⚠️ Sorry, I couldn't generate a response right now."


def read_and_reply():
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(EMAIL, PASSWORD)
    mail.select("inbox")

    result, data = mail.search(None, '(UNSEEN SUBJECT "[AI]")')
    if result == "OK":
        for num in data[0].split():
            result, msg_data = mail.fetch(num, '(RFC822)')
            if isinstance(msg_data[0], tuple):
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)
            else:
                continue

            sender = parseaddr(msg['From'])[1]

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == 'text/plain':
                        payload = part.get_payload(decode=True)
                        if payload:
                            body = payload.decode()

            else:
                body = msg.get_payload(decode=True).decode()

            prompt = body.strip()
            print(f"📩 From: {sender}\n🧠 Prompt: {prompt}")
            ai_response = get_ai_response(prompt)
            print(f"🤖 Response: {ai_response}")
            send_email(sender, "Your AI Reply", ai_response)
            print("✅ Replied to", sender)

    mail.logout()


def send_email(to, subject, body):
    msg = MIMEText(body)
    msg['From'] = EMAIL
    msg['To'] = to
    msg['Subject'] = subject

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL, PASSWORD)
        server.sendmail(EMAIL, to, msg.as_string())


# --- Your existing email-checking loop stays unchanged ---
def start_email_bot():
    while True:
        try:
            read_and_reply()
        except Exception as e:
            print("❌ Error:", e)
        time.sleep(30)

# --- New Flask web server to respond to uptime pings ---
app = Flask(__name__)

@app.route("/")
def home():
    return "✅ AI Email Bot is running!"

# --- Run email bot in parallel with web server ---
if __name__ == "__main__":
    threading.Thread(target=start_email_bot).start()
    app.run(host="0.0.0.0", port=8080)

