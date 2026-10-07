-- 008 — Alerta de link de convite restrito na faixa de saúde do painel.
--
-- Em 06/10 o convite do PromoBaby #001 foi restringido pelo WhatsApp por volta
-- das 13h10. O anúncio seguiu pagando cliques por 20h sem uma única entrada, e
-- nada no painel mudou: a API continua respondendo normal, o grupo continua
-- recebendo oferta, só o funil zera.
--
-- O monitor agora grava monitor_type = 'funil_convite' (src/monitor.py,
-- check_funis): has_error quando há FUNIL_CLIQUES_MINIMO cliques em
-- FUNIL_JANELA_HORAS sem entrada, repetido no máximo 1x/hora; e uma linha sem
-- erro quando volta a entrar gente. A view lista os grupos cujo último registro
-- da última 1h30 é de erro — some sozinho quando o funil volta ou quando o
-- monitor para de reclamar.
--
-- ciclos_24h / erros_24h / grupos_criados_24h continuam medindo só
-- 'newest_group', como antes: o alerta de funil não é erro do monitor.

CREATE OR REPLACE VIEW painel_saude_monitor AS
WITH ciclos AS (
    SELECT max(checked_at)                                                        AS ultimo_ciclo,
           (EXTRACT(EPOCH FROM (now() - max(checked_at))) / 60)::int              AS minutos_desde_ultimo_ciclo,
           count(*) FILTER (WHERE checked_at > now() - interval '24 hours')::int  AS ciclos_24h,
           count(*) FILTER (WHERE has_error
                              AND checked_at > now() - interval '24 hours')::int  AS erros_24h,
           count(*) FILTER (WHERE new_group_created
                              AND checked_at > now() - interval '24 hours')::int  AS grupos_criados_24h
      FROM monitor_logs
     WHERE monitor_type = 'newest_group'
), funil AS (
    SELECT DISTINCT ON (group_id_api) group_name, has_error
      FROM monitor_logs
     WHERE monitor_type = 'funil_convite'
       AND checked_at > now() - interval '90 minutes'
     ORDER BY group_id_api, checked_at DESC
)
SELECT ciclos.*,
       (SELECT string_agg(group_name, ', ' ORDER BY group_name)
          FROM funil WHERE has_error)                                            AS convite_suspeito
  FROM ciclos;

COMMENT ON VIEW painel_saude_monitor IS
    'Linha unica: quando o monitor rodou pela ultima vez, erros e criacoes nas ultimas 24h, '
    'e os grupos com cliques chegando e zero entradas (convite provavelmente restrito).';

GRANT SELECT ON painel_saude_monitor TO anon, authenticated;

-- Rollback: recriar a view como em 002_views_painel.sql.
