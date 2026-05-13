"""
setup_auth.py — Genera el refresh token de Google Ads OAuth.
Corre UNA VEZ en tu computador local, luego copia el token a GitHub Secrets.
"""
import os
import sys
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID     = os.getenv("GOOGLE_ADS_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_ADS_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    print("❌ Necesitas GOOGLE_ADS_CLIENT_ID y GOOGLE_ADS_CLIENT_SECRET en tu .env")
    sys.exit(1)

config = {
    "installed": {
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
        "auth_uri":      "https://accounts.google.com/o/oauth2/auth",
        "token_uri":     "https://oauth2.googleapis.com/token",
    }
}

print("\n🔐 Abriendo navegador para autenticación con Google Ads...")
print("   Inicia sesión con la cuenta que administra tu Google Ads.\n")

flow = InstalledAppFlow.from_client_config(
    config, ["https://www.googleapis.com/auth/adwords"]
)
creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")

if creds.refresh_token:
    print("\n✅ ¡Autenticación exitosa!")
    print(f"\n   GOOGLE_ADS_REFRESH_TOKEN = {creds.refresh_token}")
    print("\n   → Copia ese valor a GitHub Secrets como GOOGLE_ADS_REFRESH_TOKEN")
else:
    print("❌ No se obtuvo refresh token. Intenta de nuevo.")
    sys.exit(1)
