-- ============================================
-- SCHEMA DO BANCO DE DADOS - SUPABASE
-- ============================================
-- Tabela para gerenciar grupos de WhatsApp
-- ============================================

CREATE TABLE IF NOT EXISTS whatsapp_groups (
    -- Identificador único do registro
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

    -- ID do grupo na API do WhatsApp (JID - único, ex: 120363123456789@g.us)
    group_id_api TEXT NOT NULL UNIQUE,

    -- Nome do grupo (ex: "Dona Promo #001")
    name TEXT NOT NULL,

    -- Link de convite do grupo
    invite_link TEXT NOT NULL,

    -- Quantidade atual de membros no grupo
    member_count INTEGER DEFAULT 0 CHECK (member_count >= 0),

    -- Se o grupo está ativo (true) ou desativado (false)
    is_active BOOLEAN DEFAULT true,

    -- Campos adicionais da API UAZAPI
    subject TEXT,  -- Subject (nome/assunto do grupo)
    description TEXT,  -- Descrição do grupo (Desc)
    owner_jid TEXT,  -- JID do dono do grupo (OwnerJID)
    created_timestamp BIGINT,  -- Timestamp de criação do grupo (Creation)
    participant_version_id TEXT,  -- ParticipantVersionID
    is_announcement BOOLEAN DEFAULT false,  -- Se é grupo de anúncios (GroupIsAnnounce)
    is_locked BOOLEAN DEFAULT false,  -- Se está bloqueado (GroupIsLocked)
    is_parent BOOLEAN DEFAULT false,  -- Se é grupo pai de comunidade (IsParent)
    default_membership_approval_mode BOOLEAN DEFAULT false,  -- DefaultMembershipApprovalMode
    is_incognito BOOLEAN DEFAULT false,  -- IsIncognito
    linked_parent_jid TEXT,  -- LinkedParentJID (para grupos de comunidade)

    -- Data de criação do registro no banco
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),

    -- Data da última atualização do registro
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- ============================================
-- ÍNDICES PARA OTIMIZAÇÃO DE CONSULTAS
-- ============================================

-- Índice para buscar grupos ativos rapidamente
CREATE INDEX IF NOT EXISTS idx_groups_active
ON whatsapp_groups(is_active);

-- Índice para ordenar por quantidade de membros
CREATE INDEX IF NOT EXISTS idx_groups_member_count
ON whatsapp_groups(member_count);

-- Índice para buscar grupo mais recente
CREATE INDEX IF NOT EXISTS idx_groups_created_at
ON whatsapp_groups(created_at DESC);

-- Índice composto para o algoritmo de load balancer
-- (buscar grupo ativo com menos membros)
CREATE INDEX IF NOT EXISTS idx_groups_load_balancer
ON whatsapp_groups(is_active, member_count)
WHERE is_active = true;

-- ============================================
-- FUNÇÃO PARA ATUALIZAR updated_at AUTOMATICAMENTE
-- ============================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = TIMEZONE('utc', NOW());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para atualizar updated_at em cada UPDATE
DROP TRIGGER IF EXISTS set_updated_at ON whatsapp_groups;
CREATE TRIGGER set_updated_at
    BEFORE UPDATE ON whatsapp_groups
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- TABELA DE LOGS DE MONITORAMENTO
-- ============================================
-- Registra cada verificação do monitor (grupo mais novo e sync geral)

CREATE TABLE IF NOT EXISTS monitor_logs (
    -- Identificador único do log
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

    -- Tipo de monitoramento
    monitor_type TEXT NOT NULL CHECK (monitor_type IN ('newest_group', 'full_sync')),

    -- ID do grupo verificado (NULL para full_sync)
    group_id_api TEXT,

    -- Nome do grupo no momento da verificação
    group_name TEXT,

    -- Contagem de membros encontrada
    member_count INTEGER,

    -- Contagem anterior (para comparação)
    previous_count INTEGER,

    -- Diferença (member_count - previous_count)
    count_difference INTEGER,

    -- Se houve criação de novo grupo
    new_group_created BOOLEAN DEFAULT false,

    -- ID do novo grupo criado (se aplicável)
    new_group_id_api TEXT,

    -- Mensagem de status/observação
    status_message TEXT,

    -- Se houve erro
    has_error BOOLEAN DEFAULT false,

    -- Mensagem de erro (se aplicável)
    error_message TEXT,

    -- Timestamp da verificação
    checked_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- Índices para logs
CREATE INDEX IF NOT EXISTS idx_logs_monitor_type
ON monitor_logs(monitor_type);

CREATE INDEX IF NOT EXISTS idx_logs_group_id
ON monitor_logs(group_id_api);

CREATE INDEX IF NOT EXISTS idx_logs_checked_at
ON monitor_logs(checked_at DESC);

CREATE INDEX IF NOT EXISTS idx_logs_errors
ON monitor_logs(has_error)
WHERE has_error = true;

-- ============================================
-- POLÍTICAS DE SEGURANÇA (RLS - Row Level Security)
-- ============================================
-- Descomente e ajuste conforme sua necessidade

-- Habilita RLS
-- ALTER TABLE whatsapp_groups ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE monitor_logs ENABLE ROW LEVEL SECURITY;

-- Permite leitura para todos (se você usar chave anon)
-- CREATE POLICY "Permitir leitura pública"
-- ON whatsapp_groups FOR SELECT
-- USING (true);

-- CREATE POLICY "Permitir leitura pública logs"
-- ON monitor_logs FOR SELECT
-- USING (true);

-- Permite inserção/atualização apenas com service_role
-- CREATE POLICY "Permitir escrita com service_role"
-- ON whatsapp_groups FOR ALL
-- USING (auth.jwt() ->> 'role' = 'service_role');

-- CREATE POLICY "Permitir escrita logs com service_role"
-- ON monitor_logs FOR ALL
-- USING (auth.jwt() ->> 'role' = 'service_role');

-- ============================================
-- DADOS DE EXEMPLO (OPCIONAL)
-- ============================================
-- Descomente para inserir dados de teste

-- INSERT INTO whatsapp_groups (group_id_api, name, invite_link, member_count, is_active)
-- VALUES
--     ('120363123456789@g.us', 'Grupo 1', 'https://chat.whatsapp.com/XXXXXXXX', 850, true),
--     ('120363987654321@g.us', 'Grupo 2', 'https://chat.whatsapp.com/YYYYYYYY', 720, true),
--     ('120363111111111@g.us', 'Grupo 3', 'https://chat.whatsapp.com/ZZZZZZZZ', 300, true);

-- ============================================
-- CONSULTAS ÚTEIS
-- ============================================

-- Listar todos os grupos ativos ordenados por member_count
-- SELECT * FROM whatsapp_groups
-- WHERE is_active = true
-- ORDER BY member_count ASC;

-- Buscar grupo mais novo
-- SELECT * FROM whatsapp_groups
-- WHERE is_active = true
-- ORDER BY created_at DESC
-- LIMIT 1;

-- Buscar melhor grupo para novo lead (menos de 950 membros)
-- Sempre retorna o grupo com MENOS MEMBROS (não o mais novo)
-- SELECT * FROM whatsapp_groups
-- WHERE is_active = true AND member_count < 950
-- ORDER BY member_count ASC
-- LIMIT 1;

-- Estatísticas gerais dos grupos
-- SELECT
--     COUNT(*) as total_grupos,
--     SUM(member_count) as total_membros,
--     AVG(member_count)::INTEGER as media_membros,
--     MAX(member_count) as grupo_mais_cheio,
--     MIN(member_count) as grupo_mais_vazio
-- FROM whatsapp_groups
-- WHERE is_active = true;

-- ============================================
-- CONSULTAS ÚTEIS - LOGS DE MONITORAMENTO
-- ============================================

-- Ver últimos logs do grupo mais novo
-- SELECT * FROM monitor_logs
-- WHERE monitor_type = 'newest_group'
-- ORDER BY checked_at DESC
-- LIMIT 50;

-- Ver últimos logs de sincronização completa
-- SELECT * FROM monitor_logs
-- WHERE monitor_type = 'full_sync'
-- ORDER BY checked_at DESC
-- LIMIT 20;

-- Ver logs de quando novos grupos foram criados
-- SELECT * FROM monitor_logs
-- WHERE new_group_created = true
-- ORDER BY checked_at DESC;

-- Ver logs com erros
-- SELECT * FROM monitor_logs
-- WHERE has_error = true
-- ORDER BY checked_at DESC;

-- Histórico de crescimento de um grupo específico
-- SELECT
--     group_name,
--     member_count,
--     count_difference,
--     checked_at
-- FROM monitor_logs
-- WHERE group_id_api = '120363123456789@g.us'
-- ORDER BY checked_at DESC;

-- Estatísticas de monitoramento por tipo
-- SELECT
--     monitor_type,
--     COUNT(*) as total_verificacoes,
--     SUM(CASE WHEN has_error = true THEN 1 ELSE 0 END) as total_erros,
--     SUM(CASE WHEN new_group_created = true THEN 1 ELSE 0 END) as grupos_criados
-- FROM monitor_logs
-- GROUP BY monitor_type;

-- ============================================
-- TABELA DE LOGS DE CHAMADAS À API
-- ============================================
-- Registra todas as chamadas feitas à API do WhatsApp (UAZAPI)

CREATE TABLE IF NOT EXISTS api_call_logs (
    -- Identificador único do log
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

    -- Endpoint chamado (ex: /group/create, /group/info, /group/list)
    endpoint TEXT NOT NULL,

    -- Método HTTP (GET, POST, PUT, DELETE)
    method TEXT NOT NULL CHECK (method IN ('GET', 'POST', 'PUT', 'DELETE', 'PATCH')),

    -- Payload enviado na requisição (JSON)
    request_payload JSONB,

    -- Resposta completa da API (JSON)
    response_data JSONB,

    -- Código de status HTTP (200, 400, 500, etc)
    status_code INTEGER,

    -- Se a chamada foi bem sucedida
    success BOOLEAN DEFAULT false,

    -- Mensagem de erro (se houver)
    error_message TEXT,

    -- Duração da chamada em milissegundos
    duration_ms INTEGER,

    -- ID do grupo relacionado (se aplicável)
    group_id_api TEXT,

    -- Timestamp da chamada
    called_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- Índices para api_call_logs
CREATE INDEX IF NOT EXISTS idx_api_logs_endpoint
ON api_call_logs(endpoint);

CREATE INDEX IF NOT EXISTS idx_api_logs_group_id
ON api_call_logs(group_id_api);

CREATE INDEX IF NOT EXISTS idx_api_logs_called_at
ON api_call_logs(called_at DESC);

CREATE INDEX IF NOT EXISTS idx_api_logs_success
ON api_call_logs(success);

CREATE INDEX IF NOT EXISTS idx_api_logs_errors
ON api_call_logs(success)
WHERE success = false;

-- ============================================
-- CONSULTAS ÚTEIS - LOGS DE API
-- ============================================

-- Ver últimas chamadas à API
-- SELECT
--     endpoint,
--     method,
--     status_code,
--     success,
--     duration_ms,
--     called_at
-- FROM api_call_logs
-- ORDER BY called_at DESC
-- LIMIT 50;

-- Ver chamadas com erro
-- SELECT * FROM api_call_logs
-- WHERE success = false
-- ORDER BY called_at DESC;

-- Estatísticas de chamadas por endpoint
-- SELECT
--     endpoint,
--     method,
--     COUNT(*) as total_calls,
--     SUM(CASE WHEN success = true THEN 1 ELSE 0 END) as successful,
--     SUM(CASE WHEN success = false THEN 1 ELSE 0 END) as failed,
--     AVG(duration_ms)::INTEGER as avg_duration_ms
-- FROM api_call_logs
-- GROUP BY endpoint, method
-- ORDER BY total_calls DESC;

-- Ver histórico de chamadas de um grupo específico
-- SELECT * FROM api_call_logs
-- WHERE group_id_api = '120363123456789@g.us'
-- ORDER BY called_at DESC;
