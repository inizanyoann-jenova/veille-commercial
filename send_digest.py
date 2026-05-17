"""Script autonome — planifiable via Planificateur de tâches Windows.
Usage : python send_digest.py
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

smtp_config = {
    "host": os.getenv("DIGEST_SMTP_HOST", "smtp.gmail.com"),
    "port": int(os.getenv("DIGEST_SMTP_PORT", "587")),
    "user": os.getenv("DIGEST_SMTP_USER", ""),
    "password": os.getenv("DIGEST_SMTP_PASSWORD", ""),
    "to": os.getenv("DIGEST_TO", ""),
}

if not smtp_config["user"] or not smtp_config["to"]:
    print("❌ DIGEST_SMTP_USER et DIGEST_TO doivent être configurés dans .env")
    sys.exit(1)

from email_digest import send_digest

sent = send_digest(smtp_config)
print(f"✅ Digest envoyé" if sent else "ℹ️  Aucun nouveau marché à envoyer")
