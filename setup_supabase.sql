-- ============================================
-- SCRIPT COMPLETO PARA CONFIGURAR O SUPABASE
-- Execute este SQL no SQL Editor do Supabase
-- ============================================

-- Passo 1: Adicionar novos campos à tabela whatsapp_groups (se já existir)
ALTER TABLE IF EXISTS whatsapp_groups
ADD COLUMN IF NOT EXISTS subject TEXT,
ADD COLUMN IF NOT EXISTS description TEXT,
ADD COLUMN IF NOT EXISTS owner_jid TEXT,
ADD COLUMN IF NOT EXISTS created_timestamp BIGINT,
ADD COLUMN IF NOT EXISTS participant_version_id TEXT,
ADD COLUMN IF NOT EXISTS is_announcement BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS is_locked BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS is_parent BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS default_membership_approval_mode BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS is_incognito BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS linked_parent_jid TEXT;

-- Passo 2: Criar tabela de logs de chamadas API
CREATE TABLE IF NOT EXISTS api_call_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    endpoint TEXT NOT NULL,
    method TEXT NOT NULL CHECK (method IN ('GET', 'POST', 'PUT', 'DELETE', 'PATCH')),
    request_payload JSONB,
    response_data JSONB,
    status_code INTEGER,
    success BOOLEAN DEFAULT false,
    error_message TEXT,
    duration_ms INTEGER,
    group_id_api TEXT,
    called_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- Índices para api_call_logs
CREATE INDEX IF NOT EXISTS idx_api_logs_endpoint ON api_call_logs(endpoint);
CREATE INDEX IF NOT EXISTS idx_api_logs_group_id ON api_call_logs(group_id_api);
CREATE INDEX IF NOT EXISTS idx_api_logs_called_at ON api_call_logs(called_at DESC);
CREATE INDEX IF NOT EXISTS idx_api_logs_success ON api_call_logs(success);

-- Confirmação
SELECT 'Schema atualizado com sucesso! Pode executar o script Python agora.' as status;
