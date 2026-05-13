"""
main.py — Punto de entrada para GitHub Actions.
Recolecta métricas → analiza con IA → guarda en Supabase → genera dashboard JSON.
"""
import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__) + "/..")


def check_env():
    required = [
        "GOOGLE_ADS_DEVELOPER_TOKEN", "GOOGLE_ADS_CLIENT_ID",
        "GOOGLE_ADS_CLIENT_SECRET",   "GOOGLE_ADS_REFRESH_TOKEN",
        "GOOGLE_ADS_CUSTOMER_ID",     "GROQ_API_KEY",
        "SUPABASE_URL",               "SUPABASE_KEY",
    ]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        print(f"❌ Faltan variables de entorno: {', '.join(missing)}")
        sys.exit(1)


def generate_dashboard_data(analysis: dict, summaries: list):
    os.makedirs("dashboard", exist_ok=True)
    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "analysis":     analysis,
        "campaigns":    summaries,
    }
    with open("dashboard/data.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
    print("  📄 dashboard/data.json actualizado.")


def main():
    print("\n╔══════════════════════════════════════════╗")
    print("║     Google Ads AI Agent — GitHub Actions ║")
    print(f"║     {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}                  ║")
    print("╚══════════════════════════════════════════╝\n")

    check_env()

    print("📡 PASO 1: Recolectando métricas...")
    from agent.collector import run as collect_run
    collect_run()

    print("\n🧠 PASO 2: Analizando con Groq AI...")
    from agent.analyzer import run as analyze_run
    analysis = analyze_run()

    print("\n📄 PASO 3: Actualizando dashboard...")
    from agent.database import get_campaigns_summary
    summaries = get_campaigns_summary(days=7)
    generate_dashboard_data(analysis, summaries)

    print("\n✅ Agente completado exitosamente.")


if __name__ == "__main__":
    main()
