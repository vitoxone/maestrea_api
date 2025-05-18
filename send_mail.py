import requests
import os
from dotenv import load_dotenv

load_dotenv()


BREVO_API_KEY = os.getenv("BREVO_API_KEY")
BREVO_ENDPOINT = "https://api.brevo.com/v3/smtp/email"

def send_email(to_email: str, subject: str, text: str):
    payload = {
        "sender": {"name": "Maestrea Notifier", "email": "vsilvamella@gmail.com"},
        "to": [{"email": to_email}],
        "subject": subject,
        "textContent": text
    }

    headers = {
        "api-key": BREVO_API_KEY,
        "Content-Type": "application/json",
        "accept": "application/json"
    }

    response = requests.post(BREVO_ENDPOINT, headers=headers, json=payload)

    print(response)

    if response.status_code in (200, 201):
        print("📩 Correo enviado correctamente con Brevo.")
    else:
        print(f"❌ Error al enviar correo con Brevo: {response.status_code} — {response.text}")