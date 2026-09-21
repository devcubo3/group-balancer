-- =============================================================================
-- 005 — atribuicao de anuncio nas entradas e saidas dos grupos
-- =============================================================================
--
-- Problema: painel_fluxo_diario (002) deriva entradas/saidas da DIFERENCA de
-- member_count. Isso responde "quantos", nunca "quem" nem "de onde veio". Sem
-- isso nao da para saber se as 3 pessoas que sairam hoje vieram todas do mesmo
-- anuncio -- que e o unico jeito de flagrar um criativo que promete o que o
-- grupo nao entrega.
--
-- Como funciona, em tres pecas:
--
--   1. cliques_anuncio  — a landing grava um registro por clique no CTA, com as
--      UTMs do anuncio e o grupo para o qual mandou a pessoa.
--   2. grupo_membros    — o roster atual de cada grupo, montado pelo monitor a
--      partir do array Participants que POST /group/info JA devolve hoje
--      (whatsapp_service.py:292 so usava o len() dele).
--   3. grupo_eventos    — o diff do roster entre dois ciclos, virado em evento
--      de entrada/saida com a origem atribuida.
--
-- O link de convite do WhatsApp nao carrega parametro, entao a ligacao
-- clique->entrada e feita por PAREAMENTO POR TEMPO (ver src/membros.py). Uma
-- entrada que nao casa com nenhum clique fica como 'organica'; um empate entre
-- anuncios diferentes fica como 'ambigua' e o painel mostra isso separado, em
-- vez de fingir precisao que o metodo nao tem.
--
-- PRIVACIDADE: o JID e telefone de gente real. As tres tabelas tem RLS ligada e
-- NENHUMA policy de leitura -- nem para anon, nem para authenticated. A unica
-- coisa que anon pode fazer e INSERIR em cliques_anuncio (e so nas colunas que
-- a landing preenche). Quem escreve/le o resto e o monitor, com a service key
-- (SUPABASE_SERVICE_KEY), que ignora RLS. O painel le apenas as duas views
-- agregadas do fim deste arquivo, que nunca expoem um JID.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. cliques_anuncio — escrita pela landing page, a cada clique no CTA
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cliques_anuncio (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    criado_em     timestamptz NOT NULL DEFAULT now(),

    -- Para onde a pessoa foi mandada. group_jid e a chave do pareamento; a LP
    -- ja consulta controle_grupos no clique, entao os dois vem de graca.
    nicho_slug    text,
    grupo_id      uuid REFERENCES controle_grupos(id) ON DELETE SET NULL,
    group_jid     text,

    -- De onde ela veio. Preenchido pelas macros da Meta no campo
    -- "Parametros de URL" do anuncio; ver o comentario em LPmaeinteligente.
    utm_source    text,
    utm_medium    text,
    utm_campaign  text,
    utm_content   text,
    utm_term      text,
    utm_id        text,
    anuncio_id    text,
    conjunto_nome text,
    placement     text,
    fbclid        text,
    referrer      text,

    -- Marcado quando uma entrada consome este clique. Duas entradas no mesmo
    -- ciclo nao podem dividir o mesmo clique.
    consumido_em  timestamptz,

    -- A insercao e publica (anon). Limitar o tamanho de cada campo e a unica
    -- trava barata contra alguem inflar a tabela com lixo.
    CONSTRAINT cliques_anuncio_texto_curto CHECK (
        coalesce(length(nicho_slug),    0) <= 60  AND
        coalesce(length(group_jid),     0) <= 80  AND
        coalesce(length(utm_source),    0) <= 200 AND
        coalesce(length(utm_medium),    0) <= 200 AND
        coalesce(length(utm_campaign),  0) <= 200 AND
        coalesce(length(utm_content),   0) <= 200 AND
        coalesce(length(utm_term),      0) <= 200 AND
        coalesce(length(utm_id),        0) <= 200 AND
        coalesce(length(anuncio_id),    0) <= 200 AND
        coalesce(length(conjunto_nome), 0) <= 200 AND
        coalesce(length(placement),     0) <= 200 AND
        coalesce(length(fbclid),        0) <= 500 AND
        coalesce(length(referrer),      0) <= 500
    )
);

COMMENT ON TABLE cliques_anuncio IS
    'Um registro por clique no CTA da landing, com a origem (UTMs) e o grupo de destino. Consumido pelo pareamento em src/membros.py.';

-- Exatamente a consulta do pareamento: cliques ainda nao usados daquele grupo,
-- do mais recente para o mais antigo.
CREATE INDEX IF NOT EXISTS idx_cliques_anuncio_pareamento
    ON cliques_anuncio (group_jid, criado_em DESC)
    WHERE consumido_em IS NULL;

-- -----------------------------------------------------------------------------
-- 2. grupo_membros — roster atual (uma linha por pessoa por grupo)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS grupo_membros (
    grupo_id         uuid        NOT NULL REFERENCES controle_grupos(id) ON DELETE CASCADE,
    participante_jid text        NOT NULL,
    -- O WhatsApp esta migrando de JID de telefone para LID. Guardar os dois
    -- permite reconhecer a mesma pessoa se a API alternar entre eles -- senao
    -- ela apareceria como uma saida seguida de uma entrada, churn que nao houve.
    participante_lid text,
    entrou_em        timestamptz NOT NULL DEFAULT now(),
    visto_em         timestamptz NOT NULL DEFAULT now(),

    -- Origem herdada no momento da entrada. Fica aqui (e nao so no evento) para
    -- que a SAIDA, quando acontecer, saiba de qual anuncio a pessoa veio.
    clique_id        uuid REFERENCES cliques_anuncio(id) ON DELETE SET NULL,
    atribuicao       text NOT NULL DEFAULT 'organica'
                     CHECK (atribuicao IN ('direta', 'ambigua', 'organica', 'preexistente')),
    campanha         text,
    anuncio          text,

    PRIMARY KEY (grupo_id, participante_jid)
);

COMMENT ON TABLE grupo_membros IS
    'Roster atual de cada grupo, com a origem de cada membro. Diferenciado a cada ciclo do monitor para gerar grupo_eventos.';
COMMENT ON COLUMN grupo_membros.atribuicao IS
    'preexistente = ja estava no grupo quando o rastreio comecou (nao gera evento de entrada).';
COMMENT ON COLUMN grupo_membros.visto_em IS
    'Quando esta linha foi escrita. NAO e "conferido pela ultima vez": carimbar isso a cada ciclo custaria centenas de UPDATEs por minuto para registrar que nada mudou.';

CREATE INDEX IF NOT EXISTS idx_grupo_membros_lid
    ON grupo_membros (grupo_id, participante_lid)
    WHERE participante_lid IS NOT NULL;

-- -----------------------------------------------------------------------------
-- 3. grupo_eventos — append-only: entrada e saida com origem
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS grupo_eventos (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    grupo_id         uuid        NOT NULL REFERENCES controle_grupos(id) ON DELETE CASCADE,
    nicho_id         uuid        REFERENCES nichos(id),
    participante_jid text        NOT NULL,
    tipo             text        NOT NULL CHECK (tipo IN ('entrada', 'saida')),
    ocorrido_em      timestamptz NOT NULL DEFAULT now(),

    -- Sem FK: a retencao apaga cliques_anuncio antes de apagar o evento, e o
    -- evento precisa sobreviver ao clique que o originou.
    clique_id        uuid,
    atribuicao       text NOT NULL DEFAULT 'organica'
                     CHECK (atribuicao IN ('direta', 'ambigua', 'organica', 'preexistente')),
    -- Desnormalizados de proposito, pelo mesmo motivo do clique_id sem FK.
    campanha         text,
    anuncio          text,

    -- So em 'saida': minutos entre a entrada e a saida daquela pessoa.
    permanencia_min  integer,

    CONSTRAINT grupo_eventos_permanencia_so_na_saida
        CHECK (permanencia_min IS NULL OR tipo = 'saida')
);

COMMENT ON TABLE grupo_eventos IS
    'Entradas e saidas nominais, derivadas do diff do roster. A saida herda a origem da entrada: e isso que responde "as 3 que sairam vieram do anuncio B".';

CREATE INDEX IF NOT EXISTS idx_grupo_eventos_periodo
    ON grupo_eventos (ocorrido_em DESC);
CREATE INDEX IF NOT EXISTS idx_grupo_eventos_anuncio
    ON grupo_eventos (anuncio, tipo, ocorrido_em DESC);

-- -----------------------------------------------------------------------------
-- 4. RLS — anon so insere clique, e nunca le nada destas tabelas
-- -----------------------------------------------------------------------------
ALTER TABLE cliques_anuncio ENABLE ROW LEVEL SECURITY;
ALTER TABLE grupo_membros   ENABLE ROW LEVEL SECURITY;
ALTER TABLE grupo_eventos   ENABLE ROW LEVEL SECURITY;

-- O Supabase da GRANT ALL em toda tabela nova de public para anon e
-- authenticated (default privileges). Sem este REVOKE, o grant por coluna
-- abaixo seria inocuo e so a RLS separaria a chave publica dos telefones.
REVOKE ALL ON cliques_anuncio, grupo_membros, grupo_eventos FROM anon, authenticated;

-- Grant por COLUNA: a landing nao tem como forjar consumido_em nem criado_em,
-- que sao o que o pareamento usa para decidir.
GRANT INSERT (nicho_slug, grupo_id, group_jid,
              utm_source, utm_medium, utm_campaign, utm_content, utm_term, utm_id,
              anuncio_id, conjunto_nome, placement, fbclid, referrer)
    ON cliques_anuncio TO anon, authenticated;

DROP POLICY IF EXISTS cliques_anuncio_insert_publico ON cliques_anuncio;
CREATE POLICY cliques_anuncio_insert_publico
    ON cliques_anuncio FOR INSERT TO anon, authenticated
    WITH CHECK (true);

-- Nenhuma policy de SELECT/UPDATE/DELETE em lugar nenhum: com RLS ligada e sem
-- policy, anon fica trancado do lado de fora. service_role ignora RLS, que e
-- como o monitor escreve.

-- -----------------------------------------------------------------------------
-- 5. Views agregadas — o unico caminho do painel ate estes dados
-- -----------------------------------------------------------------------------
-- security_invoker = off (o padrao, explicitado aqui de proposito): a view roda
-- com os direitos do dono e por isso enxerga as tabelas com RLS. Ligar isso
-- deixaria o painel vazio.

-- Movimento diario por anuncio. A SAIDA e contada no dia em que aconteceu, mas
-- agrupada pelo anuncio que trouxe quem saiu -- nunca pelo anuncio que estava
-- rodando naquele dia.
CREATE OR REPLACE VIEW painel_aquisicao_diaria
WITH (security_invoker = off) AS
SELECT (ge.ocorrido_em AT TIME ZONE 'America/Sao_Paulo')::date       AS dia,
       cg.group_jid,
       cg.subject                                                    AS group_name,
       n.slug                                                        AS nicho,
       coalesce(ge.campanha, '(sem origem)')                         AS campanha,
       coalesce(ge.anuncio,  '(sem origem)')                         AS anuncio,
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
 GROUP BY 1, 2, 3, 4, 5, 6;

COMMENT ON VIEW painel_aquisicao_diaria IS
    'Entradas/saidas por dia, grupo e anuncio de ORIGEM. Agregada: nunca expoe participante_jid.';

-- Coorte por anuncio nos ultimos 90 dias: de tudo que este anuncio trouxe,
-- quanto ficou. E a leitura de "quebra de expectativa".
--
-- entradas e saidas sao contadas direto dos eventos (a saida ja carrega o
-- anuncio de origem), sem join entre elas: quem entra, sai e volta a entrar
-- multiplicaria as linhas de um join e inflaria os dois numeros.
CREATE OR REPLACE VIEW painel_aquisicao_anuncio
WITH (security_invoker = off) AS
SELECT coalesce(ge.campanha, '(sem origem)')                          AS campanha,
       coalesce(ge.anuncio,  '(sem origem)')                          AS anuncio,
       n.slug                                                         AS nicho,
       count(*) FILTER (WHERE ge.tipo = 'entrada')::int               AS entradas,
       count(*) FILTER (WHERE ge.tipo = 'saida')::int                 AS saidas,
       greatest(count(*) FILTER (WHERE ge.tipo = 'entrada')
                - count(*) FILTER (WHERE ge.tipo = 'saida'), 0)::int  AS ainda_no_grupo,
       CASE WHEN count(*) FILTER (WHERE ge.tipo = 'entrada') > 0
            THEN round(100.0 * greatest(count(*) FILTER (WHERE ge.tipo = 'entrada')
                                        - count(*) FILTER (WHERE ge.tipo = 'saida'), 0)
                             / count(*) FILTER (WHERE ge.tipo = 'entrada'))::int
       END                                                            AS retencao_pct,
       percentile_cont(0.5) WITHIN GROUP (
           ORDER BY ge.permanencia_min
       ) FILTER (WHERE ge.tipo = 'saida')::int                        AS permanencia_mediana_min,
       count(*) FILTER (WHERE ge.tipo = 'entrada'
                          AND ge.atribuicao = 'ambigua')::int         AS entradas_ambiguas,
       min(ge.ocorrido_em) FILTER (WHERE ge.tipo = 'entrada')         AS primeira_entrada,
       max(ge.ocorrido_em) FILTER (WHERE ge.tipo = 'entrada')         AS ultima_entrada
  FROM grupo_eventos ge
  LEFT JOIN nichos n ON n.id = ge.nicho_id
 WHERE ge.ocorrido_em > now() - interval '90 days'
 GROUP BY 1, 2, 3;

COMMENT ON VIEW painel_aquisicao_anuncio IS
    'Coorte de 90 dias por anuncio: entradas, saidas de quem veio dele, retencao e permanencia mediana. A retencao e aproximada nas bordas da janela.';

GRANT SELECT ON painel_aquisicao_diaria, painel_aquisicao_anuncio TO anon, authenticated;

-- -----------------------------------------------------------------------------
-- 6. Retencao — mesmo formato de 003_retencao_monitor_logs.sql
-- -----------------------------------------------------------------------------
-- 180 dias casa com a janela de painel_aquisicao_diaria: encurtar cegaria o
-- painel. Os cliques saem antes (90 dias) porque depois de pareados eles nao
-- sao mais lidos por ninguem -- a origem ja vive desnormalizada no evento.
CREATE OR REPLACE FUNCTION limpar_aquisicao_antiga()
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  apagadas integer;
  total    integer;
BEGIN
  DELETE FROM grupo_eventos WHERE ocorrido_em <= now() - interval '180 days';
  GET DIAGNOSTICS total = ROW_COUNT;

  DELETE FROM cliques_anuncio WHERE criado_em <= now() - interval '90 days';
  GET DIAGNOSTICS apagadas = ROW_COUNT;

  RETURN total + apagadas;
END;
$$;

COMMENT ON FUNCTION limpar_aquisicao_antiga() IS
  'Remove grupo_eventos > 180d e cliques_anuncio > 90d. As janelas casam com painel_aquisicao_diaria (180d) e com o pareamento, que so olha os ultimos minutos.';

-- Funcao nasce executavel por PUBLIC, e o PostgREST a expoe como
-- /rest/v1/rpc/limpar_aquisicao_antiga para a chave anon. So o pg_cron chama.
REVOKE EXECUTE ON FUNCTION limpar_aquisicao_antiga() FROM PUBLIC, anon, authenticated;

-- 04:40 UTC: logo depois de limpar-monitor-logs (04:30), fora do pico.
SELECT cron.schedule(
  'limpar-aquisicao',
  '40 4 * * *',
  $$SELECT limpar_aquisicao_antiga();$$
);

-- Verificacao:
--   -- com a chave ANON, o insert passa e a leitura NAO:
--   --   POST /rest/v1/cliques_anuncio   (header Prefer: return=minimal) -> 201
--   --   GET  /rest/v1/cliques_anuncio   -> 401/permission denied
--   SELECT * FROM painel_aquisicao_diaria ORDER BY dia DESC LIMIT 20;
--   SELECT * FROM painel_aquisicao_anuncio ORDER BY retencao_pct NULLS LAST;
--   SELECT jobname, schedule FROM cron.job WHERE jobname = 'limpar-aquisicao';
--
-- Rollback:
--   SELECT cron.unschedule('limpar-aquisicao');
--   DROP VIEW IF EXISTS painel_aquisicao_diaria, painel_aquisicao_anuncio;
--   DROP FUNCTION IF EXISTS limpar_aquisicao_antiga();
--   DROP TABLE IF EXISTS grupo_eventos, grupo_membros, cliques_anuncio;
