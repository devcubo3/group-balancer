-- =============================================================================
-- 004 — dia do painel no fuso de São Paulo
-- =============================================================================
--
-- Já aplicada em produção (migration Supabase `painel_fluxo_diario_fuso_brasil`,
-- 2026-09-12). Fica aqui para o repositório registrar o que existe no banco.
--
-- O banco roda em UTC. Com `checked_at::date`, entre 21h e 0h no Brasil o dia
-- já virava: às 23h do dia 12 o painel mostrava "Hoje" como o dia 13, quase
-- vazio. Com os atalhos "Ontem" e o calendário, o corte errado passaria a
-- mostrar o dia errado inteiro. O corte agora é America/Sao_Paulo; a janela de
-- 90 dias continua sobre `checked_at`, que é um instante e não depende de fuso.
--
-- Mesmas colunas e tipos da 002 — CREATE OR REPLACE é suficiente.
-- =============================================================================

CREATE OR REPLACE VIEW painel_fluxo_diario AS
WITH s AS (
    SELECT ml.group_id_api,
           ml.group_name,
           ml.checked_at,
           (ml.checked_at AT TIME ZONE 'America/Sao_Paulo')::date AS dia,
           ml.member_count,
           lag(ml.member_count) OVER (
               PARTITION BY ml.group_id_api ORDER BY ml.checked_at
           ) AS anterior
      FROM monitor_logs ml
     WHERE ml.monitor_type = 'newest_group'
       AND ml.member_count IS NOT NULL
       AND ml.group_id_api IS NOT NULL
       AND ml.checked_at > now() - interval '90 days'
)
SELECT s.dia,
       s.group_id_api,
       s.group_name,
       n.slug                                                         AS nicho,
       cg.status                                                      AS status_grupo,
       sum(greatest(s.member_count - s.anterior, 0))::int              AS entradas,
       sum(greatest(s.anterior - s.member_count, 0))::int              AS saidas,
       sum(s.member_count - s.anterior)::int                           AS saldo,
       (array_agg(s.member_count ORDER BY s.checked_at DESC))[1]::int  AS membros_fim_do_dia,
       count(*)::int                                                   AS amostras
  FROM s
  LEFT JOIN controle_grupos cg ON cg.group_jid = s.group_id_api
  LEFT JOIN nichos n           ON n.id = cg.nicho_id
 WHERE s.anterior IS NOT NULL
 GROUP BY s.dia, s.group_id_api, s.group_name, n.slug, cg.status;

COMMENT ON VIEW painel_fluxo_diario IS
    'Entradas/saidas/saldo por grupo por dia (dia no fuso America/Sao_Paulo), derivados da serie de member_count em monitor_logs. Janela de 90 dias.';

GRANT SELECT ON painel_fluxo_diario TO anon, authenticated;

-- Rollback: reaplicar migrations/002_views_painel.sql (volta ao corte em UTC).
