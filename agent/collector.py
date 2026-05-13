"""
collector.py — Recolecta métricas reales de Google Ads API.
"""
import os
from datetime import date, timedelta
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from agent.database import save_metrics, save_alert

CUSTOMER_ID = os.environ["GOOGLE_ADS_CUSTOMER_ID"]
CAMPAIGN_IDS = [c.strip() for c in os.environ.get("CAMPAIGN_IDS", "").split(",") if c.strip()]


def build_client() -> GoogleAdsClient:
    return GoogleAdsClient.load_from_dict({
        "developer_token": os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"],
        "client_id":       os.environ["GOOGLE_ADS_CLIENT_ID"],
        "client_secret":   os.environ["GOOGLE_ADS_CLIENT_SECRET"],
        "refresh_token":   os.environ["GOOGLE_ADS_REFRESH_TOKEN"],
        "use_proto_plus":  True,
    })


def collect(target_date: date) -> list[dict]:
    date_str = target_date.isoformat()
    print(f"  📡 Recolectando métricas para {date_str}...")

    client     = build_client()
    ga_service = client.get_service("GoogleAdsService")

    campaign_filter = ""
    if CAMPAIGN_IDS:
        ids = ", ".join(CAMPAIGN_IDS)
        campaign_filter = f"AND campaign.id IN ({ids})"

    query = f"""
        SELECT
            campaign.id,
            campaign.name,
            segments.date,
            segments.hour,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.conversions_value,
            metrics.ctr,
            metrics.average_cpc,
            metrics.search_impression_share
        FROM campaign
        WHERE segments.date = '{date_str}'
          AND campaign.status != 'REMOVED'
          {campaign_filter}
        ORDER BY campaign.id, segments.hour
    """

    records = []
    try:
        stream = ga_service.search_stream(customer_id=CUSTOMER_ID, query=query)
        for batch in stream:
            for row in batch.results:
                cost   = row.metrics.cost_micros / 1_000_000
                conv   = row.metrics.conversions
                val    = row.metrics.conversions_value
                cpa    = round(cost / conv, 4) if conv > 0 else 0
                roas   = round(val / cost, 4)  if cost > 0 else 0
                imp_sh = row.metrics.search_impression_share

                rec = {
                    "campaign_id":             str(row.campaign.id),
                    "campaign_name":           row.campaign.name,
                    "date":                    row.segments.date,
                    "hour":                    row.segments.hour,
                    "impressions":             row.metrics.impressions,
                    "clicks":                  row.metrics.clicks,
                    "cost_usd":                round(cost, 4),
                    "conversions":             conv,
                    "conversion_value":        val,
                    "ctr":                     round(row.metrics.ctr * 100, 4),
                    "avg_cpc":                 round(row.metrics.average_cpc / 1_000_000, 4),
                    "cpa":                     cpa,
                    "roas":                    roas,
                    "search_impression_share": round(imp_sh * 100, 2) if imp_sh else 0,
                }
                records.append(rec)
                _auto_alert(rec)

    except GoogleAdsException as ex:
        print(f"  ❌ Google Ads API error: {ex.error.code().name}")
        for err in ex.failure.errors:
            print(f"     {err.message}")
        raise

    print(f"  ✅ {len(records)} registros recolectados.")
    return records


def _auto_alert(m: dict):
    """Alertas en tiempo real por métricas críticas."""
    cid   = m["campaign_id"]
    cname = m["campaign_name"]
    h     = m["hour"]

    if m["impressions"] > 500 and m["ctr"] < 0.5:
        save_alert(cid, cname, "LOW_CTR", "warning",
            f"CTR muy bajo ({m['ctr']:.2f}%) con {m['impressions']:,} impresiones · hora {h}h")

    if m["cost_usd"] > 10 and m["conversions"] == 0:
        save_alert(cid, cname, "SPEND_NO_CONV", "critical",
            f"${m['cost_usd']:.2f} gastados sin conversiones · hora {h}h")

    if m["roas"] > 0 and m["roas"] < 1.0:
        save_alert(cid, cname, "LOW_ROAS", "warning",
            f"ROAS negativo ({m['roas']:.2f}x) · hora {h}h — perdiendo dinero")


def run():
    today     = date.today()
    yesterday = today - timedelta(days=1)
    for d in [yesterday, today]:
        records = collect(d)
        if records:
            save_metrics(records)
