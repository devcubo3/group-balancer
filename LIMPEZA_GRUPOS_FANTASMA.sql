-- =============================================================================
-- LIMPEZA DOS GRUPOS FANTASMA — incidente de 2026-09-12
-- =============================================================================
--
-- NADA AQUI FOI EXECUTADO. Revise, rode o passo 1, confira, depois rode o 2.
--
-- O QUE ACONTECEU
-- `get_newest_group()` devolvia NULL tanto para "nicho sem grupo" quanto para
-- "a consulta ao Supabase falhou". O monitor lia esse NULL como nicho vazio e
-- criava um grupo novo. Entre 05:35 e 14:01 de 2026-09-12 nasceram 8 grupos
-- duplicados — todos chamados "#001", porque aquele branch hardcodava o número.
--
-- POR QUE ISSO DÓI ALÉM DA BAGUNÇA NA LISTA DO WHATSAPP
--   1. bot-divulgador/src/supabase_client.py:65 dispara TODA oferta para TODO
--      grupo status='ativo' do nicho → 5 grupos vazios do geral e 3 do bebes
--      recebendo cada oferta (queima de API e risco de flag de spam).
--   2. LPCarameloOfertas/lib/grupo.ts:26 ordena por membros_atuais CRESCENTE →
--      o grupo mais vazio ganha. Desde 05:35 todo lead de /grupo/<slug> caiu
--      num fantasma em vez do grupo real. É o dano maior.
--
-- ANTES DE RODAR: pare o serviço `group-balancer` no Dokploy, senão ele cria
-- mais fantasmas enquanto você limpa.
--
-- =============================================================================
-- PASSO 0 — o caso ambíguo, decida primeiro
-- =============================================================================
--
-- "Mãe Inteligente #001" / JID 120363428366456401@g.us / id
-- bfb76ab9-292e-4c6b-987d-0e51ef100dfe, criado 2026-09-12 01:20:27, 4 membros.
--
-- Este NÃO é um fantasma do bug: nasceu num intervalo em que o monitor estava
-- parado (monitor_logs param 01:19 e só voltam 03:14) e não tem registro de
-- new_group_created. Tem cara de criação manual durante o rebrand
-- PromoBaby → Mãe Inteligente. É também o que tem mais gente dentro.
--
-- Ele NÃO está incluído nos comandos abaixo. Se foi você que criou e ele é o
-- #002 legítimo da cadeia do bebes, renomeie em vez de arquivar:
--
--   UPDATE controle_grupos SET subject = 'Mãe Inteligente #002'
--    WHERE id = 'bfb76ab9-292e-4c6b-987d-0e51ef100dfe';
--
-- Se foi acidente, acrescente o id dele à lista do PASSO 2.

-- =============================================================================
-- PASSO 1 — conferir a lista antes de mexer (só leitura)
-- =============================================================================

SELECT cg.id,
       n.slug             AS nicho,
       cg.subject,
       cg.membros_atuais,
       cg.link_convite,
       cg.created_at
  FROM controle_grupos cg
  JOIN nichos n ON n.id = cg.nicho_id
 WHERE cg.id IN (
    -- geral: cadeia real é "Caramelo Ofertas #023"
    '7564863c-48f1-4696-8fca-3aff81bb246d',  -- 05:35, 1 membro
    'f27a589f-e521-4409-a8ca-9731dda9d283',  -- 06:15, 1 membro
    'c767d2dd-2105-40b0-afa5-f5432929bbff',  -- 09:06, 1 membro
    '88e598d5-75e5-42e2-a995-c91f59a15ff7',  -- 12:01, 1 membro
    '73d4d1f5-80b5-46bd-b590-52ced213a765',  -- 14:01, 1 membro
    -- bebes: cadeia real é "PromoBaby #001" (56 membros)
    '73e47106-8276-476d-8f2a-2c0e096f0384',  -- 07:25, 2 MEMBROS REAIS
    '24726295-04e9-49c0-a434-2fff828857dd',  -- 08:35, 1 membro
    '9f80b8af-9c83-4837-9cd4-2e92095e86c9'   -- 09:00, 1 membro
 )
 ORDER BY n.slug, cg.created_at;

-- Esperado: 8 linhas. `membros_atuais` pode estar defasado — o monitor só
-- sincronizava o grupo mais novo de cada nicho, então os fantasmas mais antigos
-- pararam de ser atualizados quando um mais novo nasceu. Confira no WhatsApp
-- pelo link antes de arquivar, principalmente o de 07:25.

-- =============================================================================
-- PASSO 2 — arquivar
-- =============================================================================
--
-- `status='arquivado'` basta: o bot-divulgador filtra status='ativo' e a LP
-- também, então eles param de receber ofertas e somem do redirect na hora.
-- Os grupos continuam existindo no WhatsApp — quem já entrou não é expulso, e
-- você decide depois se apaga ou se avisa a galera.

UPDATE controle_grupos
   SET status = 'arquivado'
 WHERE id IN (
    '7564863c-48f1-4696-8fca-3aff81bb246d',
    'f27a589f-e521-4409-a8ca-9731dda9d283',
    'c767d2dd-2105-40b0-afa5-f5432929bbff',
    '88e598d5-75e5-42e2-a995-c91f59a15ff7',
    '73d4d1f5-80b5-46bd-b590-52ced213a765',
    '73e47106-8276-476d-8f2a-2c0e096f0384',
    '24726295-04e9-49c0-a434-2fff828857dd',
    '9f80b8af-9c83-4837-9cd4-2e92095e86c9'
 );
-- Esperado: UPDATE 8

-- =============================================================================
-- PASSO 3 — conferir que sobrou só a cadeia legítima
-- =============================================================================

SELECT n.slug, cg.subject, cg.membros_atuais, cg.ordem_sequencial
  FROM controle_grupos cg
  JOIN nichos n ON n.id = cg.nicho_id
 WHERE cg.status = 'ativo'
 ORDER BY n.slug, cg.ordem_sequencial;

-- Esperado (se você arquivou também o do PASSO 0):
--   bebes | PromoBaby #001        | 56 | 1
--   geral | Caramelo Ofertas #023 | 47 | 1

-- Nenhum subject repetido dentro de um nicho:
SELECT nicho_id, subject, count(*)
  FROM controle_grupos
 WHERE status = 'ativo'
 GROUP BY 1, 2
HAVING count(*) > 1;
-- Esperado: 0 linhas

-- =============================================================================
-- PASSO 4 — só depois da limpeza, aplicar migrations/001_guard_grupo_duplicado.sql
-- =============================================================================
--
-- O índice único parcial recusa um segundo grupo ativo com o mesmo nome no
-- mesmo nicho. Com os duplicados ainda ativos, a criação do índice falha — é de
-- propósito: ele só existe depois que a casa está limpa.
