-- 009 — Failover de convite restrito.
--
-- Em 06/10 o WhatsApp restringiu o convite do PromoBaby #001 por 7 dias — nem
-- pelo celular dava para gerar link novo. O grupo segue vivo (415 membros
-- recebendo oferta), só não pode receber gente nova.
--
-- `convite_restrito_ate` separa as duas coisas, sem mexer em `status`:
--   - status = 'ativo' continua dizendo "recebe oferta" (bot-divulgador);
--   - convite_restrito_ate > now() diz "não mande lead para cá" (landings).
--
-- Quem escreve: o group-balancer (src/monitor.py, check_funis) quando vê
-- cliques chegando e zero entradas, ou um UPDATE manual. Quem reage: o próprio
-- monitor, que abre o próximo grupo da cadeia quando nenhum grupo ativo do
-- nicho tem convite disponível, e as landings, que pulam o grupo marcado.
-- NULL = convite normal. Rollback de um grupo: UPDATE ... SET convite_restrito_ate = NULL.

ALTER TABLE controle_grupos ADD COLUMN IF NOT EXISTS convite_restrito_ate timestamptz;

COMMENT ON COLUMN controle_grupos.convite_restrito_ate IS
    'Ate quando o convite esta restrito pelo WhatsApp. Grupo segue recebendo oferta; landings o pulam. NULL = normal.';

-- Painel: o alerta passa a listar também os grupos marcados, não só os que
-- dispararam o alerta na última 1h30 — senão a faixa ficava verde 90 min
-- depois do failover, com o grupo ainda restrito.
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
), suspeitos AS (
    SELECT group_name FROM funil WHERE has_error
    UNION
    SELECT subject FROM controle_grupos
     WHERE status = 'ativo' AND convite_restrito_ate > now()
)
SELECT ciclos.*,
       (SELECT string_agg(group_name, ', ' ORDER BY group_name) FROM suspeitos) AS convite_suspeito
  FROM ciclos;

GRANT SELECT ON painel_saude_monitor TO anon, authenticated;
