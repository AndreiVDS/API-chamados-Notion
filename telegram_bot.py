import os
import requests
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")  # Coloque o ID do grupo aqui ou no .env

def enviar_mensagem_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensagem,
        "parse_mode": "Markdown"  # ou "HTML"
    }

    try:
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            print("❌ Erro ao enviar mensagem para o Telegram:", response.text)
        else:
            print("✅ Mensagem enviada com sucesso ao grupo do Telegram.")
    except Exception as e:
        print("❌ Exceção ao enviar mensagem:", str(e))
