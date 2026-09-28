-- =============================================================================
-- 007 — a coorte volta a separar campanha
-- =============================================================================
--
-- 006 agrupou painel_aquisicao_coorte por CRIATIVO, juntando o mesmo anuncio
-- rodando em campanhas diferentes. O motivo era legitimo -- o criativo e a
-- unidade da decisao criativa, e antes o CTV 08 aparecia em 4 linhas com 37%,
-- 53%, 57% e 83% sem nenhuma indicacao de amostra.
--
-- Mas o GASTO e por campanha. Sem separar, nenhuma linha da tabela pode ser
-- cruzada com o custo do Gerenciador, e custo por membro que fica -- que e a
-- unica regra de decisao que importa nesta operacao -- fica impossivel de
-- calcular. Um mesmo criativo em BIDCAP e em BIDCAP TESTE V2 tem lance, verba e
-- custo por lead diferentes; somar os dois esconde justamente o que decide.
--
-- O problema que motivou o agrupamento continua resolvido por outro caminho, de
-- 006: toda taxa carrega base_1h/base_48h, o painel mostra a amostra entre
-- parenteses e o realce so dispara com base >= 20. Amostra pequena agora se
-- denuncia sozinha, sem precisar somar linhas que nao deveriam ser somadas.
-- =============================================================================

CREATE OR REPLACE VIEW painel_aquisicao_coorte
WITH (security_invoker = off) AS
WITH entradas AS (
    SELECT e.grupo_id, e.participante_jid, e.ocorrido_em AS entrou,
           e.nicho_id, e.campanha, e.anuncio
      FROM grupo_eventos e
     WHERE e.tipo = 'entrada'
       AND e.atribuicao <> 'preexistente'
       AND e.ocorrido_em > now() - interval '90 days'
), pareado AS MATERIALIZED (
    -- MATERIALIZED de proposito: sem isto o Postgres inlineia a CTE e recalcula
    -- a subconsulta de saida uma vez por coluna que a usa (4 vezes, visto no
    -- EXPLAIN). Com a tabela crescendo, seria 4x o custo por nada.
    SELECT en.*,
           (SELECT min(s.ocorrido_em)
              FROM grupo_eventos s
             WHERE s.tipo = 'saida'
               AND s.grupo_id = en.grupo_id
               AND s.participante_jid = en.participante_jid
               AND s.ocorrido_em > en.entrou) AS saiu
      FROM entradas en
)
SELECT coalesce(p.anuncio,  '(organico)')                             AS anuncio,
       -- A chave nova. Cada linha passa a corresponder a uma linha de gasto do
       -- Gerenciador de Anuncios.
       coalesce(p.campanha, '(sem campanha)')                         AS campanha,
       n.slug                                                         AS nicho,
       count(*)::int                                                  AS entradas,

       count(*) FILTER (WHERE p.entrou <= now() - interval '1 hour')::int   AS base_1h,
       count(*) FILTER (WHERE p.entrou <= now() - interval '1 hour'
                          AND p.saiu  <= p.entrou + interval '1 hour')::int AS saiu_1h,

       count(*) FILTER (WHERE p.entrou <= now() - interval '48 hours')::int AS base_48h,
       count(*) FILTER (WHERE p.entrou <= now() - interval '48 hours'
                          AND p.saiu  <= p.entrou + interval '48 hours')::int AS saiu_48h,

       count(*) FILTER (WHERE p.entrou > now() - interval '24 hours')::int  AS entradas_verdes,

       round(percentile_cont(0.5) WITHIN GROUP (
           ORDER BY extract(epoch FROM (p.saiu - p.entrou)) / 60
       ) FILTER (WHERE p.saiu IS NOT NULL))::int                      AS permanencia_mediana_min
  FROM pareado p
  LEFT JOIN nichos n ON n.id = p.nicho_id
 GROUP BY 1, 2, 3;

COMMENT ON VIEW painel_aquisicao_coorte IS
    'Coorte por criativo E campanha: cada linha casa com uma linha de gasto do Gerenciador, que e o que permite calcular custo por membro que fica. Cada taxa tem seu proprio denominador de maturidade (base_1h, base_48h). Agregada: nunca expoe participante_jid.';

-- Verificacao:
--   SELECT anuncio, campanha, entradas, saiu_1h, base_1h, saiu_48h, base_48h
--     FROM painel_aquisicao_coorte ORDER BY entradas DESC;
--   -- CTV 05 IMG deve aparecer em 2 linhas (BIDCAP e BIDCAP TESTE V2)
--   -- CTV 08 em 4 (ALL, V2, BIDCAP, BIDCAP TESTE), somando 137 entradas
--
-- Rollback: restaurar a view de 006_coorte_aquisicao.sql (GROUP BY 1, 2).
