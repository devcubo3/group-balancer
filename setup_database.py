#!/usr/bin/env python3
"""
Script para configurar o banco de dados Supabase automaticamente
"""
import sys
from pathlib import Path

# Adiciona o diretório src ao path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from supabase import create_client
from src.config import settings


def setup_database():
    """Configura o banco de dados com as tabelas necessárias"""
    
    print("\n" + "="*60)
    print("CONFIGURANDO BANCO DE DADOS SUPABASE")
    print("="*60 + "\n")
    
    # Conecta ao Supabase
    print("🔌 Conectando ao Supabase...")
    client = create_client(settings.supabase_url, settings.supabase_key)
    print("✓ Conectado!\n")
    
    # SQL para adicionar novos campos à tabela whatsapp_groups
    print("📝 Adicionando novos campos à tabela whatsapp_groups...")
    
    alter_table_sql = """
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
    """
    
    try:
        client.postgrest.rpc('exec', {'query': alter_table_sql}).execute()
        print("✓ Campos adicionados com sucesso!\n")
    except Exception as e:
        print(f"⚠ Campos já existem ou erro: {e}\n")
    
    # SQL para criar tabela de logs de API
    print("📝 Criando tabela api_call_logs...")
    
    create_logs_table_sql = """
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
    
    CREATE INDEX IF NOT EXISTS idx_api_logs_endpoint ON api_call_logs(endpoint);
    CREATE INDEX IF NOT EXISTS idx_api_logs_group_id ON api_call_logs(group_id_api);
    CREATE INDEX IF NOT EXISTS idx_api_logs_called_at ON api_call_logs(called_at DESC);
    CREATE INDEX IF NOT EXISTS idx_api_logs_success ON api_call_logs(success);
    """
    
    try:
        # Tenta criar a tabela verificando se existe
        result = client.table('api_call_logs').select('id').limit(1).execute()
        print("✓ Tabela api_call_logs já existe!\n")
    except:
        print("⚠ Tabela api_call_logs não existe, será necessário criar via SQL Editor\n")
        print("Execute este SQL no Supabase SQL Editor:")
        print("-" * 60)
        print(create_logs_table_sql)
        print("-" * 60 + "\n")
    
    # Verifica tabelas existentes
    print("📋 Verificando tabelas existentes...")
    
    try:
        # Tenta acessar whatsapp_groups
        groups = client.table('whatsapp_groups').select('id').limit(1).execute()
        print("✓ Tabela whatsapp_groups: OK")
    except Exception as e:
        print(f"✗ Tabela whatsapp_groups: NÃO ENCONTRADA - {e}")
        print("\nExecute o SQL completo do arquivo docs/SUPABASE_SCHEMA.sql primeiro!")
        return False
    
    try:
        # Tenta acessar monitor_logs
        logs = client.table('monitor_logs').select('id').limit(1).execute()
        print("✓ Tabela monitor_logs: OK")
    except Exception as e:
        print(f"✗ Tabela monitor_logs: NÃO ENCONTRADA - {e}")
    
    try:
        # Tenta acessar api_call_logs
        api_logs = client.table('api_call_logs').select('id').limit(1).execute()
        print("✓ Tabela api_call_logs: OK")
    except Exception as e:
        print(f"✗ Tabela api_call_logs: PRECISA SER CRIADA")
    
    print("\n" + "="*60)
    print("✅ CONFIGURAÇÃO CONCLUÍDA!")
    print("="*60 + "\n")
    
    return True


if __name__ == "__main__":
    try:
        success = setup_database()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ ERRO: {e}\n")
        sys.exit(1)
