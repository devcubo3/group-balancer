-- 003 - Retencao de monitor_logs em 90 dias
--
-- Problema: a tabela crescia sem limite desde 2026-01-06. Chegou a 96.430
-- linhas / 26 MB e nunca passou por autovacuum -- as estatisticas estavam tao
-- defasadas que pg_stat_user_tables reportava 1.350 linhas vivas.
--
-- O monitor roda 2.436 ciclos/dia (medido em painel_saude_monitor), e cada
-- ciclo insere uma linha. Com o Supabase avisando esgotamento de recursos, essa
-- era a tabela de maior crescimento do projeto, e a view painel_fluxo_diario --
-- que faz window function sobre ela -- era a consulta mais cara do banco: 20%
-- do tempo total de execucao, 385ms de media.
--
-- Solucao: as duas unicas views que consomem monitor_logs ja ignoram o que
-- passa de 90 dias (painel_fluxo_diario filtra checked_at > now()-90d em
-- 002_views_painel.sql:31; painel_saude_monitor olha so 24h). Tudo alem disso
-- era peso morto mantido a cada escrita. A limpeza inicial removeu 55.105
-- linhas (57% da tabela) sem alterar uma unica linha visivel em qualquer view.
--
-- Aplicado em producao em 2026-09-12 junto de:
--   - CREATE INDEX idx_monitor_logs_painel  (serve painel_fluxo_diario)
--   - REINDEX ofertas_embedding_hnsw        (15 MB de bloat -> 16 kB)
-- Banco: 102 MB -> 90 MB.

CREATE OR REPLACE FUNCTION limpar_monitor_logs_antigos()
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  apagadas integer;
BEGIN
  DELETE FROM monitor_logs WHERE checked_at <= now() - interval '90 days';
  GET DIAGNOSTICS apagadas = ROW_COUNT;
  RETURN apagadas;
END;
$$;

COMMENT ON FUNCTION limpar_monitor_logs_antigos() IS
  'Remove monitor_logs com mais de 90 dias. A janela casa com painel_fluxo_diario, que so le os ultimos 90 dias: encurtar este intervalo cegaria o painel.';

-- 04:30 UTC: fora do horario de pico e sem colidir com delete-expired-ofertas
-- (de hora em hora) nem com cleanup-expired-offers (03:00).
SELECT cron.schedule(
  'limpar-monitor-logs',
  '30 4 * * *',
  $$SELECT limpar_monitor_logs_antigos();$$
);

-- Indice que serve painel_fluxo_diario: o filtro e por monitor_type, e a window
-- function particiona por group_id_api ordenando por checked_at. O WHERE parcial
-- casa com a condicao member_count IS NOT NULL da view.
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_monitor_logs_painel
  ON monitor_logs (monitor_type, group_id_api, checked_at)
  WHERE member_count IS NOT NULL;

-- Verificacao:
--   SELECT count(*), min(checked_at) FROM monitor_logs;
--   SELECT * FROM painel_saude_monitor;
--   SELECT jobname, schedule FROM cron.job WHERE jobname = 'limpar-monitor-logs';
