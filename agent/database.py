"""
database.py — Todas las operaciones con Supabase.
"""
import os
import json
from datetime import date, timedelta
from supabase import create_client, Client

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_KEY"]
        _client = create_client(url, key)
    return _client


# ── Métricas ────────────────────────────────────────────────────────────────

def save_metrics(metrics_list: list[dict]):
    """Inserta métricas horarias. Si ya existe el registro (campaign+date+hour), lo actualiza."""
    if not metrics_list:
        return
    db = get_client()
    db.table("hourly_metrics").upsert(
        metrics_list,
        on_conflict="campaign_id,date,hour"
    ).execute()
    print(f"  💾 {len(metrics_list)} registros guardados en Supabase.")


def get_historical_metrics(days: int = 30) -> list[dict]:
    since = (date.today() - timedelta(days=days)).isoformat()
    db = get_client()
    res = (
        db.table("hourly_metrics")
        .select("*")
        .gte("date", since)
        .order("date", desc=True)
        .order("hour", desc=True)
        .limit(2000)
        .execute()
    )
    return res.data or []


def get_campaigns_summary(days: int = 7) -> list[dict]:
    """Usa la vista campaign_summary_7d (o hace la query directa para otros rangos)."""
    if days == 7:
        db = get_client()
        res = db.table("campaign_summary_7d").select("*").execute()
        return res.data or []

    since = (date.today() - timedelta(days=days)).isoformat()
    db = get_client()
    res = (
        db.table("hourly_metrics")
        .select("campaign_id,campaign_name,impressions,clicks,cost_usd,conversions,conversion_value,ctr,avg_cpc")
        .gte("date", since)
        .execute()
    )
    rows = res.data or []

    # Agregar en Python
    agg: dict[str, dict] = {}
    for r in rows:
        cid = r["campaign_id"]
        if cid not in agg:
            agg[cid] = {
                "campaign_id": cid,
                "campaign_name": r["campaign_name"],
                "total_impressions": 0, "total_clicks": 0,
                "total_cost": 0.0, "total_conversions": 0.0,
                "total_value": 0.0, "ctr_sum": 0.0, "n": 0,
            }
        a = agg[cid]
        a["total_impressions"]  += r.get("impressions", 0)
        a["total_clicks"]       += r.get("clicks", 0)
        a["total_cost"]         += float(r.get("cost_usd", 0))
        a["total_conversions"]  += float(r.get("conversions", 0))
        a["total_value"]        += float(r.get("conversion_value", 0))
        a["ctr_sum"]            += float(r.get("ctr", 0))
        a["n"]                  += 1

    result = []
    for a in agg.values():
        n = a["n"] or 1
        cost = a["total_cost"]
        conv = a["total_conversions"]
        val  = a["total_value"]
        result.append({
            "campaign_id":       a["campaign_id"],
            "campaign_name":     a["campaign_name"],
            "total_impressions": a["total_impressions"],
            "total_clicks":      a["total_clicks"],
            "total_cost":        round(cost, 4),
            "total_conversions": round(conv, 2),
            "total_value":       round(val, 2),
            "avg_ctr":           round(a["ctr_sum"] / n, 4),
            "avg_cpa":           round(cost / conv, 4) if conv > 0 else 0,
            "avg_roas":          round(val / cost, 4)  if cost > 0 else 0,
        })
    return sorted(result, key=lambda x: x["total_cost"], reverse=True)


# ── Análisis IA ──────────────────────────────────────────────────────────────

def save_analysis(analysis: dict):
    db = get_client()
    db.table("ai_analyses").insert({
        "campaign_ids":        analysis.get("campaign_ids", []),
        "overall_score":       analysis.get("overall_score", 0),
        "period_summary":      analysis.get("period_summary", ""),
        "insights":            analysis.get("insights", []),
        "opportunities":       analysis.get("opportunities", []),
        "alerts":              analysis.get("alerts", []),
        "recommended_actions": analysis.get("recommended_actions", []),
    }).execute()


def get_recent_analyses(limit: int = 5) -> list[dict]:
    db = get_client()
    res = (
        db.table("ai_analyses")
        .select("*")
        .order("analyzed_at", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data or []


# ── Alertas ──────────────────────────────────────────────────────────────────

def save_alert(campaign_id: str, campaign_name: str, alert_type: str, severity: str, message: str):
    db = get_client()
    db.table("realtime_alerts").insert({
        "campaign_id":   campaign_id,
        "campaign_name": campaign_name,
        "alert_type":    alert_type,
        "severity":      severity,
        "message":       message,
    }).execute()
