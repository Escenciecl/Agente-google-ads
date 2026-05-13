"""
analyzer.py — Analiza campañas con Groq AI (gratis) usando historial completo de Supabase.
Modelo: llama-3.3-70b-versatile
"""
import os
import json
from groq import Groq
from agent.database import (
    get_campaigns_summary,
    get_historical_metrics,
    get_recent_analyses,
    save_analysis,
)

client = Groq(api_key=os.environ["GROQ_API_KEY"])

SYSTEM_PROMPT = """Eres un experto senior en Google Ads con 15 años de experiencia
maximizando ventas y ROAS para empresas en Latinoamérica y España.

Analizas datos históricos de campañas y entregas insights accionables para vender más.
Siempre basas tus conclusiones en los números reales. Eres directo y priorizas impacto en ventas.

IMPORTANTE: Si en el historial hay análisis previos, evalúa si las acciones anteriores
tuvieron efecto positivo o negativo en los datos actuales. Aprende del historial.

Responde ÚNICAMENTE con JSON válido, sin texto adicional ni backticks. Estructura:
{
  "overall_score": <0-100>,
  "period_summary": "<resumen ejecutivo 2-3 oraciones con los números más importantes>",
  "insights": [
    {
      "tipo": "oportunidad|problema|tendencia|patron",
      "titulo": "<título corto>",
      "descripcion": "<descripción con datos específicos y números>",
      "impacto_estimado": "<impacto concreto en ventas o ROAS>",
      "urgencia": "alta|media|baja"
    }
  ],
  "opportunities": [
    {
      "titulo": "<oportunidad específica>",
      "descripcion": "<qué está pasando con datos>",
      "potencial": "<estimación de mejora en %>",
      "accion": "<pasos concretos a seguir>"
    }
  ],
  "alerts": [
    {
      "severidad": "critica|alta|media",
      "campana": "<nombre campaña>",
      "problema": "<descripción del problema con números>",
      "solucion": "<solución inmediata>"
    }
  ],
  "recommended_actions": [
    {
      "prioridad": <1-5>,
      "accion": "<acción específica>",
      "razon": "<por qué hacerlo ahora>",
      "impacto_esperado": "<resultado esperado con estimación>"
    }
  ]
}"""


def build_prompt(summaries: list, historical: list, prev_analyses: list) -> str:
    from datetime import date, timedelta
    two_days_ago = (date.today() - timedelta(days=2)).isoformat()
    recent_48h = [h for h in historical if str(h.get("date", "")) >= two_days_ago][:300]

    memory_block = ""
    if prev_analyses:
        last = prev_analyses[0]
        memory_block = f"""
═══ MEMORIA HISTÓRICA — ANÁLISIS ANTERIOR ═══
Fecha: {last.get('analyzed_at', 'N/A')}
Score anterior: {last.get('overall_score', 'N/A')}/100
Resumen: {last.get('period_summary', '')}
Oportunidades identificadas: {json.dumps(last.get('opportunities', []), ensure_ascii=False)}
Acciones recomendadas: {json.dumps(last.get('recommended_actions', []), ensure_ascii=False)}
Alertas anteriores: {json.dumps(last.get('alerts', []), ensure_ascii=False)}

→ Evalúa si hubo mejora vs las métricas actuales. Menciona qué funcionó y qué no.
═══════════════════════════════════════════════
"""

    return f"""Analiza estas campañas de Google Ads para maximizar ventas.

FECHA DEL ANÁLISIS: {date.today().isoformat()}
CAMPAÑAS ANALIZADAS: {len(summaries)}

RESUMEN ÚLTIMOS 7 DÍAS (por campaña):
{json.dumps(summaries, indent=2, ensure_ascii=False)}

MÉTRICAS HORARIAS — ÚLTIMAS 48 HORAS (para detectar patrones por hora del día):
{json.dumps(recent_48h, indent=2, ensure_ascii=False)}

{memory_block}

Analiza especialmente:
1. ¿Qué horas del día tienen mejor tasa de conversión? (ajustes de puja por hora)
2. ¿Qué campañas tienen ROAS negativo? (están perdiendo dinero)
3. ¿Qué campañas están limitadas por presupuesto con buen ROAS? (oportunidad de escalar)
4. ¿Hay tendencia de mejora o deterioro vs la semana anterior?
5. ¿Dónde está la mayor oportunidad de aumentar ventas con el mismo presupuesto?"""


def run() -> dict:
    print("  🧠 Iniciando análisis con Claude AI...")

    summaries    = get_campaigns_summary(days=7)
    historical   = get_historical_metrics(days=30)
    prev_analyses = get_recent_analyses(limit=3)

    if not summaries:
        print("  ⚠️  Sin datos de campañas para analizar.")
        return {}

    print(f"  📊 {len(summaries)} campañas · {len(historical)} registros históricos · {len(prev_analyses)} análisis previos")

    prompt = build_prompt(summaries, historical, prev_analyses)

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.3,
        max_tokens=4096,
        response_format={"type": "json_object"},  # Fuerza JSON válido
    )

    raw = response.choices[0].message.content.strip()

    analysis = json.loads(raw)
    analysis["campaign_ids"] = [s["campaign_id"] for s in summaries]

    save_analysis(analysis)

    score = analysis.get("overall_score", 0)
    print(f"  ✅ Análisis completado · Score: {score}/100")
    print(f"     {len(analysis.get('insights', []))} insights · "
          f"{len(analysis.get('opportunities', []))} oportunidades · "
          f"{len(analysis.get('alerts', []))} alertas")

    return analysis
