-- =============================================================================
-- 006 — coorte de aquisicao: retencao medida com denominador de maturidade
-- =============================================================================
--
-- Problema, medido em 28/09. O criativo `CTV 05 IMG` e o pior que a operacao ja
-- rodou: 15% de quem entra por ele sai em MENOS DE UMA HORA (o CTV 08 fica em
-- 4%), e no mesmo posicionamento -- Instagram Stories -- sao 14% contra 0%.
-- Sair em menos de uma hora e a assinatura de quebra de expectativa: nao deu
-- tempo de o grupo fazer nada, a pessoa entrou, olhou e voltou.
--
-- E o painel mostrava esse criativo como o MELHOR da tabela, com 62%.
--
-- A causa: painel_aquisicao_anuncio (005) calcula
--     retencao = (entradas - saidas) / entradas
-- sobre a janela inteira, sem olhar quanto tempo cada pessoa teve de exposicao.
-- O CTV 05 IMG tinha 75% das entradas com menos de 24h (idade media 21h); o
-- CTV 08, idade media de 92h. A view comparava uma coorte de ontem com uma da
-- semana passada e chamava as duas de "retencao" -- e o painel, do jeito que
-- estava, mandaria escalar o criativo que estava queimando a verba.
--
-- A correcao tem duas partes:
--   1. contar PESSOAS, nao eventos: parear cada entrada com a saida seguinte
--      daquela mesma pessoa, e so entao perguntar "saiu em quanto tempo";
--   2. cada taxa carrega o proprio denominador de maturidade -- a de 1h so
--      considera quem entrou ha pelo menos 1h, a de 48h idem.
--
-- Tambem separa a base anterior ao rastreio: `preexistente` aparecia somado aos
-- organicos numa linha "(sem origem)" com 10 entradas, 42 saidas e saldo -32.
-- Aquelas saidas sao de quem ja estava no grupo antes de 21/09 -- nao pertencem
-- a anuncio nenhum, e poluiam o topo da tabela.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. A coorte por criativo
-- -----------------------------------------------------------------------------
-- Agrupa por ANUNCIO, nao por campanha: o criativo e a unidade da decisao. Antes
-- o CTV 08 aparecia em 4 linhas (37%, 53%, 57%, 83%) e o numero dele nunca
-- aparecia. As campanhas que o usaram vao no array, para o painel mostrar como
-- subtitulo.
CREATE OR REPLACE VIEW painel_aquisicao_coorte
WITH (security_invoker = off) AS
WITH entradas AS (
    SELECT e.grupo_id, e.participante_jid, e.ocorrido_em AS entrou,
           e.nicho_id, e.campanha, e.anuncio
      FROM grupo_eventos e
     WHERE e.tipo = 'entrada'
       -- Quem ja estava no grupo quando o rastreio comecou nao veio de anuncio.
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
SELECT coalesce(p.anuncio, '(organico)')                              AS anuncio,
       n.slug                                                         AS nicho,
       count(*)::int                                                  AS entradas,

       -- Saida em 1h: a assinatura de quebra de expectativa. Denominador proprio.
       count(*) FILTER (WHERE p.entrou <= now() - interval '1 hour')::int   AS base_1h,
       count(*) FILTER (WHERE p.entrou <= now() - interval '1 hour'
                          AND p.saiu  <= p.entrou + interval '1 hour')::int AS saiu_1h,

       -- Retencao de 48h: horizonte em que a evasao ja se manifestou quase toda.
       count(*) FILTER (WHERE p.entrou <= now() - interval '48 hours')::int AS base_48h,
       count(*) FILTER (WHERE p.entrou <= now() - interval '48 hours'
                          AND p.saiu  <= p.entrou + interval '48 hours')::int AS saiu_48h,

       -- Entradas jovens demais para julgar. Acima de metade do total, o painel
       -- marca a linha como "maturando" e nao a realca em sentido nenhum.
       count(*) FILTER (WHERE p.entrou > now() - interval '24 hours')::int  AS entradas_verdes,

       round(percentile_cont(0.5) WITHIN GROUP (
           ORDER BY extract(epoch FROM (p.saiu - p.entrou)) / 60
       ) FILTER (WHERE p.saiu IS NOT NULL))::int                      AS permanencia_mediana_min,

       array_agg(DISTINCT coalesce(p.campanha, '(sem campanha)'))     AS campanhas
  FROM pareado p
  LEFT JOIN nichos n ON n.id = p.nicho_id
 GROUP BY 1, 2;

COMMENT ON VIEW painel_aquisicao_coorte IS
    'Coorte por criativo: cada taxa com seu proprio denominador de maturidade. Substitui painel_aquisicao_anuncio, que comparava coortes de idades diferentes. Agregada: nunca expoe participante_jid.';

-- A subconsulta de saida roda uma vez por entrada.
CREATE INDEX IF NOT EXISTS idx_grupo_eventos_saida_pessoa
    ON grupo_eventos (grupo_id, participante_jid, ocorrido_em)
    WHERE tipo = 'saida';

-- -----------------------------------------------------------------------------
-- 2. A base anterior ao rastreio, com numero proprio
-- -----------------------------------------------------------------------------
-- E o vazamento de fundo do grupo (medido em ~4%/dia), que nao pertence a
-- anuncio nenhum e por isso nao cabe na tabela de criativos.
CREATE OR REPLACE VIEW painel_evasao_base
WITH (security_invoker = off) AS
SELECT (ge.ocorrido_em AT TIME ZONE 'America/Sao_Paulo')::date AS dia,
       n.slug                                                  AS nicho,
       count(*)::int                                           AS saidas_base,
       (SELECT count(*)::int
          FROM grupo_membros m
          JOIN controle_grupos g ON g.id = m.grupo_id
         WHERE m.atribuicao = 'preexistente'
           AND g.nicho_id = ge.nicho_id)                       AS restantes_na_base
  FROM grupo_eventos ge
  LEFT JOIN nichos n ON n.id = ge.nicho_id
 WHERE ge.tipo = 'saida'
   AND ge.atribuicao = 'preexistente'
   AND ge.ocorrido_em > now() - interval '90 days'
 GROUP BY 1, 2, ge.nicho_id;

COMMENT ON VIEW painel_evasao_base IS
    'Saidas de quem ja estava no grupo antes do rastreio, por dia. Fora da tabela de anuncios de proposito: nao tem origem e distorcia o topo dela.';

-- -----------------------------------------------------------------------------
-- 3. painel_aquisicao_diaria deixa de contar a base antiga
-- -----------------------------------------------------------------------------
-- Mesmas colunas de 005 (o painel publicado continua lendo), so o filtro novo:
-- e uma view de aquisicao, e `preexistente` nao foi adquirido.
CREATE OR REPLACE VIEW painel_aquisicao_diaria
WITH (security_invoker = off) AS
SELECT (ge.ocorrido_em AT TIME ZONE 'America/Sao_Paulo')::date       AS dia,
       cg.group_jid,
       cg.subject                                                    AS group_name,
       n.slug                                                        AS nicho,
       coalesce(ge.campanha, '(sem campanha)')                       AS campanha,
       -- Mesmo rotulo de painel_aquisicao_coorte: o painel cruza as duas views
       -- por este campo, e dois nomes para a mesma coisa quebram o cruzamento.
       coalesce(ge.anuncio,  '(organico)')                           AS anuncio,
       count(*) FILTER (WHERE ge.tipo = 'entrada')::int              AS entradas,
       count(*) FILTER (WHERE ge.tipo = 'saida')::int                AS saidas,
       (count(*) FILTER (WHERE ge.tipo = 'entrada')
        - count(*) FILTER (WHERE ge.tipo = 'saida'))::int            AS saldo,
       count(*) FILTER (WHERE ge.tipo = 'entrada'
                          AND ge.atribuicao = 'ambigua')::int        AS entradas_ambiguas
  FROM grupo_eventos ge
  LEFT JOIN controle_grupos cg ON cg.id = ge.grupo_id
  LEFT JOIN nichos n           ON n.id = ge.nicho_id
 WHERE ge.ocorrido_em > now() - interval '180 days'
   AND ge.atribuicao <> 'preexistente'
 GROUP BY 1, 2, 3, 4, 5, 6;

GRANT SELECT ON painel_aquisicao_coorte, painel_evasao_base TO anon, authenticated;

-- painel_aquisicao_anuncio fica no banco, sem uso, ate o painel novo estar no
-- ar. Dropar em migration separada -- senao existe uma janela em que o painel
-- publicado le uma view que nao existe mais.

-- Verificacao (numeros de 28/09):
--   SELECT anuncio, entradas, saiu_1h, base_1h, saiu_48h, base_48h, entradas_verdes
--     FROM painel_aquisicao_coorte ORDER BY entradas DESC;
--   -- CTV 05 IMG: entradas 53, saiu_1h 8/53, base_48h 5, verdes 40
--   -- CTV 08:     entradas 137, saiu_1h 6/137, saiu_48h 37/99
--
-- Rollback:
--   DROP VIEW IF EXISTS painel_aquisicao_coorte, painel_evasao_base;
--   DROP INDEX IF EXISTS idx_grupo_eventos_saida_pessoa;
--   -- e restaurar painel_aquisicao_diaria de 005_atribuicao_anuncios.sql
