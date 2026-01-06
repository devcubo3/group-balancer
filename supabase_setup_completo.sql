-- ============================================
-- SETUP COMPLETO DO BANCO DE DADOS SUPABASE
-- Execute este SQL no SQL Editor do Supabase
-- ============================================

-- ============================================
-- 1. TABELA DE GRUPOS DE WHATSAPP
-- ============================================

CREATE TABLE IF NOT EXISTS whatsapp_groups (
    -- Identificador único do registro
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    
    -- ID do grupo na API do WhatsApp (JID - único, ex: 120363123456789@g.us)
    group_id_api TEXT NOT NULL UNIQUE,
    
    -- Nome do grupo
    name TEXT NOT NULL,
    
    -- Link de convite do grupo
    invite_link TEXT DEFAULT '',
    
    -- Quantidade atual de membros no grupo
    member_count INTEGER DEFAULT 0 CHECK (member_count >= 0),
    
    -- Se o grupo está ativo (true) ou desativado (false)
    is_active BOOLEAN DEFAULT true,
    
    -- Campos da API UAZAPI
    subject TEXT,  -- Nome/assunto do grupo (Name na API)
    description TEXT,  -- Descrição/tópico do grupo (Topic na API)
    owner_jid TEXT,  -- JID do dono do grupo (OwnerJID)
    created_timestamp TEXT,  -- Timestamp de criação (GroupCreated)
    participant_version_id TEXT,  -- ParticipantVersionID
    is_announcement BOOLEAN DEFAULT false,  -- IsAnnounce
    is_locked BOOLEAN DEFAULT false,  -- IsLocked
    is_parent BOOLEAN DEFAULT false,  -- IsParent
    default_membership_approval_mode TEXT,  -- DefaultMembershipApprovalMode
    is_incognito BOOLEAN DEFAULT false,  -- IsIncognito
    linked_parent_jid TEXT,  -- LinkedParentJID
    
    -- Timestamps do registro
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- Índices para otimização
CREATE INDEX IF NOT EXISTS idx_groups_active ON whatsapp_groups(is_active);
CREATE INDEX IF NOT EXISTS idx_groups_member_count ON whatsapp_groups(member_count);
CREATE INDEX IF NOT EXISTS idx_groups_created_at ON whatsapp_groups(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_groups_load_balancer ON whatsapp_groups(is_active, member_count) WHERE is_active = true;

-- ============================================
-- 2. TABELA DE LOGS DE MONITORAMENTO
-- ============================================

CREATE TABLE IF NOT EXISTS monitor_logs (
    -- Identificador único do log
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    
    -- Tipo de monitoramento ('newest_group' ou 'full_sync')
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

-- Índices para logs de monitoramento
CREATE INDEX IF NOT EXISTS idx_logs_monitor_type ON monitor_logs(monitor_type);
CREATE INDEX IF NOT EXISTS idx_logs_group_id ON monitor_logs(group_id_api);
CREATE INDEX IF NOT EXISTS idx_logs_checked_at ON monitor_logs(checked_at DESC);
CREATE INDEX IF NOT EXISTS idx_logs_errors ON monitor_logs(has_error) WHERE has_error = true;

-- ============================================
-- 3. TABELA DE LOGS DE CHAMADAS À API
-- ============================================

CREATE TABLE IF NOT EXISTS api_call_logs (
    -- Identificador único do log
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    
    -- Endpoint chamado (ex: /group/create, /group/info)
    endpoint TEXT NOT NULL,
    
    -- Método HTTP (GET, POST, PUT, DELETE, PATCH)
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

-- Índices para logs de API
CREATE INDEX IF NOT EXISTS idx_api_logs_endpoint ON api_call_logs(endpoint);
CREATE INDEX IF NOT EXISTS idx_api_logs_group_id ON api_call_logs(group_id_api);
CREATE INDEX IF NOT EXISTS idx_api_logs_called_at ON api_call_logs(called_at DESC);
CREATE INDEX IF NOT EXISTS idx_api_logs_success ON api_call_logs(success);
CREATE INDEX IF NOT EXISTS idx_api_logs_errors ON api_call_logs(success) WHERE success = false;

-- ============================================
-- 4. TRIGGER PARA ATUALIZAR updated_at
-- ============================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = TIMEZONE('utc', NOW());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS set_updated_at ON whatsapp_groups;
CREATE TRIGGER set_updated_at
    BEFORE UPDATE ON whatsapp_groups
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- CONFIRMAÇÃO
-- ============================================

SELECT 'Banco de dados configurado com sucesso!' as status,
       'Tabelas criadas: whatsapp_groups, monitor_logs, api_call_logs' as info;
