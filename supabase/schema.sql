-- =============================================
-- Google Ads AI Agent — Schema Supabase
-- Ejecutar en: Supabase → SQL Editor
-- =============================================

create table if not exists hourly_metrics (
    id                      bigserial primary key,
    collected_at            timestamptz default now(),
    campaign_id             text not null,
    campaign_name           text,
    date                    date not null,
    hour                    int not null,
    impressions             bigint default 0,
    clicks                  bigint default 0,
    cost_usd                numeric(12,4) default 0,
    conversions             numeric(10,2) default 0,
    conversion_value        numeric(12,2) default 0,
    ctr                     numeric(8,4) default 0,
    avg_cpc                 numeric(10,4) default 0,
    cpa                     numeric(10,4) default 0,
    roas                    numeric(10,4) default 0,
    search_impression_share numeric(6,2) default 0,
    unique (campaign_id, date, hour)
);

create table if not exists ai_analyses (
    id                  bigserial primary key,
    analyzed_at         timestamptz default now(),
    campaign_ids        jsonb default '[]',
    overall_score       int default 0,
    period_summary      text,
    insights            jsonb default '[]',
    opportunities       jsonb default '[]',
    alerts              jsonb default '[]',
    recommended_actions jsonb default '[]'
);

create table if not exists realtime_alerts (
    id          bigserial primary key,
    created_at  timestamptz default now(),
    campaign_id text,
    campaign_name text,
    alert_type  text,
    severity    text,
    message     text,
    resolved    boolean default false
);

-- Índices para consultas rápidas
create index if not exists idx_metrics_date        on hourly_metrics(date desc);
create index if not exists idx_metrics_campaign    on hourly_metrics(campaign_id, date desc);
create index if not exists idx_analyses_date       on ai_analyses(analyzed_at desc);
create index if not exists idx_alerts_created      on realtime_alerts(created_at desc);

-- Vista útil: resumen por campaña últimos 7 días
create or replace view campaign_summary_7d as
select
    campaign_id,
    campaign_name,
    sum(impressions)                                        as total_impressions,
    sum(clicks)                                             as total_clicks,
    sum(cost_usd)                                           as total_cost,
    sum(conversions)                                        as total_conversions,
    sum(conversion_value)                                   as total_value,
    round(avg(ctr)::numeric, 4)                             as avg_ctr,
    round(avg(avg_cpc)::numeric, 4)                         as avg_cpc,
    case when sum(conversions) > 0
         then round((sum(cost_usd)/sum(conversions))::numeric, 4)
         else 0 end                                         as avg_cpa,
    case when sum(cost_usd) > 0
         then round((sum(conversion_value)/sum(cost_usd))::numeric, 4)
         else 0 end                                         as avg_roas
from hourly_metrics
where date >= current_date - interval '7 days'
group by campaign_id, campaign_name
order by total_cost desc;

-- RLS: deshabilitado (usamos service_role key desde el agente)
alter table hourly_metrics      disable row level security;
alter table ai_analyses         disable row level security;
alter table realtime_alerts     disable row level security;
