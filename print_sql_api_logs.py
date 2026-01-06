#!/usr/bin/env python3
"""
Script para criar a tabela api_call_logs no Supabase via SQL Editor manual
"""

sql_create_table = """
-- Criar tabela de logs de chamadas API
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

SELECT 'Tabela api_call_logs criada com sucesso!' as status;
"""

print("\n" + "="*70)
print("SQL PARA CRIAR TABELA api_call_logs NO SUPABASE")
print("="*70)
print("\nCopie o SQL abaixo e execute no SQL Editor do Supabase:")
print("\n" + "-"*70)
print(sql_create_table)
print("-"*70 + "\n")
print("Depois execute novamente: python create_first_group.py\n")
