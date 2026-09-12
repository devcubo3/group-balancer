-- =============================================================================
-- 002 — views de leitura para o painel de grupos
-- =============================================================================
--
-- Já aplicada em produção (migration Supabase `views_painel_grupos`,
-- 2026-09-12). Fica aqui para o repositório registrar o que existe no banco.
--
-- O cálculo de entradas/saídas precisa de window function (lag) sobre a série
-- de member_count, que o PostgREST não expressa. Pré-agregar aqui mantém a
-- página leve: ela busca ~1 linha por dia por grupo em vez de ~1400 amostras
-- cruas. Todas são SELECT-only e recebem GRANT apenas de leitura.
-- =============================================================================

-- Fluxo diário por grupo: entradas e saídas separadas, nunca só o saldo.
-- A série é amostrada de minuto em minuto pelo monitor, então a soma das
-- variações positivas entre amostras consecutivas aproxima bem as entradas, e a
-- das negativas as saídas. Quem entra e sai dentro do mesmo minuto não aparece.
CREATE OR REPLACE VIEW painel_fluxo_diario AS
WITH s AS (
    SELECT ml.group_id_api,
           ml.group_name,
           ml.checked_at,
           ml.checked_at::date AS dia,
           ml.member_count,
           lag(ml.member_count) OVER (
               PARTITION BY ml.group_id_api ORDER BY ml.checked_at
           ) AS anterior
      FROM monitor_logs ml
     WHERE ml.monitor_type = 'newest_group'
       AND ml.member_count IS NOT NULL
       AND ml.group_id_api IS NOT NULL
       -- Janela limitada: mantém a window function barata conforme a tabela cresce
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
    'Entradas/saidas/saldo por grupo por dia, derivados da serie de member_count em monitor_logs. Janela de 90 dias. Usado pelo painel de grupos.';

-- Um grupo por linha, com o nicho já resolvido.
CREATE OR REPLACE VIEW painel_grupos AS
SELECT cg.id,
       cg.group_jid,
       cg.subject           AS nome,
       n.slug               AS nicho,
       n.nome_grupo         AS marca_nicho,
       cg.status,
       cg.membros_atuais,
       cg.capacidade_max,
       cg.ordem_sequencial,
       cg.link_convite,
       cg.created_at
  FROM controle_grupos cg
  LEFT JOIN nichos n ON n.id = cg.nicho_id;

COMMENT ON VIEW painel_grupos IS 'Grupos com nicho resolvido, para o painel.';

-- Saúde do monitor. Se ele para, todo o resto do painel congela sem avisar —
-- foi exatamente assim que o bug de 2026-09-12 passou horas despercebido, e é
-- por isso que esta faixa vem antes de qualquer número na página.
CREATE OR REPLACE VIEW painel_saude_monitor AS
SELECT max(checked_at)                                                        AS ultimo_ciclo,
       (EXTRACT(EPOCH FROM (now() - max(checked_at))) / 60)::int              AS minutos_desde_ultimo_ciclo,
       count(*) FILTER (WHERE checked_at > now() - interval '24 hours')::int  AS ciclos_24h,
       count(*) FILTER (WHERE has_error
                          AND checked_at > now() - interval '24 hours')::int  AS erros_24h,
       count(*) FILTER (WHERE new_group_created
                          AND checked_at > now() - interval '24 hours')::int  AS grupos_criados_24h
  FROM monitor_logs
 WHERE monitor_type = 'newest_group';

COMMENT ON VIEW painel_saude_monitor IS
    'Linha unica: quando o monitor rodou pela ultima vez, erros e criacoes nas ultimas 24h.';

GRANT SELECT ON painel_fluxo_diario, painel_grupos, painel_saude_monitor TO anon, authenticated;

-- Rollback:
-- DROP VIEW IF EXISTS painel_fluxo_diario, painel_grupos, painel_saude_monitor;
