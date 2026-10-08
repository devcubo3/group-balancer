-- =============================================================================
-- 010 — painel_fluxo_diario passa a enxergar todos os grupos ativos
-- =============================================================================
--
-- A view lia so monitor_type = 'newest_group', gravado apenas para o grupo mais
-- novo de cada nicho. Em 07/10 o failover de convite restrito abriu o Mae
-- Inteligente #002 e o PromoBaby #001 deixou de ser o mais novo: a serie dele
-- parou em 415 enquanto o grupo ia a 410 (5 saidas, todas em grupo_eventos).
--
-- O monitor agora grava monitor_type = 'roster' para cada grupo ativo a cada
-- ROSTER_INTERVAL_MIN (src/monitor.py, check_rosters). A view le as duas.
-- Para o grupo mais novo as amostras se intercalam, o que nao conta nada em
-- dobro: o lag mede a variacao de uma unica contagem real. So `amostras` cresce.
--
-- painel_saude_monitor NAO muda: mede o ciclo de 60s e segue so em newest_group.
-- O indice (monitor_type, group_id_api, checked_at) da 003 continua servindo.
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
     WHERE ml.monitor_type IN ('newest_group', 'roster')
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
       (array_agg(s.member_count ORDER BY s.checked_at DESC))[1]       AS membros_fim_do_dia,
       count(*)::int                                                   AS amostras
  FROM s
  LEFT JOIN controle_grupos cg ON cg.group_jid = s.group_id_api
  LEFT JOIN nichos n           ON n.id = cg.nicho_id
 WHERE s.anterior IS NOT NULL
 GROUP BY s.dia, s.group_id_api, s.group_name, n.slug, cg.status;

COMMENT ON VIEW painel_fluxo_diario IS
    'Entradas/saidas/saldo por grupo por dia (fuso America/Sao_Paulo), derivados da serie de member_count em monitor_logs (newest_group + roster). Janela de 90 dias.';

-- Backfill (rodado uma vez, 2026-10-08): o buraco do PromoBaby #001 desde o
-- failover, reconstruido das saidas nominais de grupo_eventos — uma amostra no
-- instante de cada saida, descendo de 415.
--
-- INSERT INTO monitor_logs (monitor_type, group_id_api, group_name, member_count, status_message, checked_at)
-- SELECT 'roster', cg.group_jid, cg.subject,
--        415 - row_number() OVER (ORDER BY e.ocorrido_em),
--        'Backfill 010: reconstruido de grupo_eventos', e.ocorrido_em
--   FROM grupo_eventos e JOIN controle_grupos cg ON cg.id = e.grupo_id
--  WHERE cg.subject = 'PromoBaby #001' AND e.tipo = 'saida'
--    AND e.ocorrido_em > '2026-10-07 14:27:17+00';
--
-- Segundo backfill (2026-10-08): o deploy atrasou e 08/10 ficou sem amostra.
-- Soma acumulada de entradas (+1) e saidas (-1) a partir de 408 (00:43 UTC),
-- fechando em 402, igual a controle_grupos.membros_atuais.
--
-- INSERT INTO monitor_logs (monitor_type, group_id_api, group_name, member_count, status_message, checked_at)
-- SELECT 'roster', cg.group_jid, cg.subject,
--        408 + sum(CASE e.tipo WHEN 'entrada' THEN 1 ELSE -1 END) OVER (ORDER BY e.ocorrido_em),
--        'Backfill 010: reconstruido de grupo_eventos', e.ocorrido_em
--   FROM grupo_eventos e JOIN controle_grupos cg ON cg.id = e.grupo_id
--  WHERE cg.subject = 'PromoBaby #001'
--    AND e.ocorrido_em > '2026-10-08 00:43:47+00';

-- Rollback: reaplicar a definicao de 004_painel_dia_fuso_brasil.sql.
