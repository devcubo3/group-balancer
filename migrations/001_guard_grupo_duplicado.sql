-- =============================================================================
-- 001 — backstop contra grupo duplicado no mesmo nicho
-- =============================================================================
--
-- Última linha de defesa do incidente de 2026-09-12, em que uma falha de
-- leitura no Supabase virou 8 grupos "#001" duplicados recebendo ofertas e
-- roubando todos os leads da landing page (que redireciona para o grupo com
-- menos membros).
--
-- A correção de verdade está no código (guard de dupla confirmação + cooldown
-- em src/monitor.py, e src/supabase_client.py levantando em vez de devolver
-- NULL quando a consulta falha). Este índice existe para o caso de a lógica
-- falhar de novo por outro caminho: o INSERT é recusado e nenhum grupo fantasma
-- chega a receber tráfego.
--
-- Limite conhecido: não impede o grupo já ter sido criado na UazAPI — aí sobra
-- um grupo órfão no WhatsApp, sem linha no banco. Quem evita isso é o cooldown,
-- que roda ANTES da chamada de API. Órfão é bem menos pior que fantasma ativo.
--
-- PRÉ-REQUISITO: rodar LIMPEZA_GRUPOS_FANTASMA.sql primeiro. Com duplicados
-- ainda ativos a criação do índice falha — de propósito.
-- =============================================================================

CREATE UNIQUE INDEX IF NOT EXISTS controle_grupos_nicho_subject_ativo_uniq
    ON controle_grupos (nicho_id, subject)
 WHERE status = 'ativo';

COMMENT ON INDEX controle_grupos_nicho_subject_ativo_uniq IS
    'Um nicho não pode ter dois grupos ATIVOS com o mesmo nome. Arquivados '
    'ficam de fora porque a numeração é histórica: "#001" arquivado e "#024" '
    'ativo convivem. Ver group-balancer/LIMPEZA_GRUPOS_FANTASMA.sql.';

-- Rollback:
-- DROP INDEX IF EXISTS controle_grupos_nicho_subject_ativo_uniq;
