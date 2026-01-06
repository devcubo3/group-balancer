#!/usr/bin/env python3
"""
Script para configurar as tabelas do Supabase automaticamente
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from postgrest import APIError
from supabase import create_client
from src.config import settings


def setup_tables():
    """Cria as tabelas necessárias no Supabase"""
    
    print("\n" + "="*70)
    print("CONFIGURANDO TABELAS NO SUPABASE")
    print("="*70 + "\n")
    
    # Conecta ao Supabase
    print("🔌 Conectando ao Supabase...")
    client = create_client(settings.supabase_url, settings.supabase_key)
    print("✓ Conectado!\n")
    
    # Lê o arquivo SQL
    sql_file = Path(__file__).parent / "supabase_setup_completo.sql"
    print(f"📄 Lendo SQL de: {sql_file}\n")
    
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    print("📝 SQL pronto para execução")
    print("-" * 70)
    print("\n⚠️  IMPORTANTE: Execute o SQL manualmente no Supabase SQL Editor")
    print("\nAcesse: https://supabase.com")
    print("1. Faça login no seu projeto")
    print("2. Vá em 'SQL Editor' no menu lateral")
    print(f"3. Cole e execute o conteúdo do arquivo: {sql_file}")
    print("\nPressione ENTER quando terminar...")
    input()
    
    # Verifica se as tabelas foram criadas
    print("\n" + "="*70)
    print("VERIFICANDO TABELAS")
    print("="*70 + "\n")
    
    tables_ok = True
    
    # Testa whatsapp_groups
    try:
        client.table('whatsapp_groups').select('id').limit(1).execute()
        print("✓ Tabela whatsapp_groups: OK")
    except Exception as e:
        print(f"✗ Tabela whatsapp_groups: ERRO - {e}")
        tables_ok = False
    
    # Testa monitor_logs
    try:
        client.table('monitor_logs').select('id').limit(1).execute()
        print("✓ Tabela monitor_logs: OK")
    except Exception as e:
        print(f"✗ Tabela monitor_logs: ERRO - {e}")
        tables_ok = False
    
    # Testa api_call_logs
    try:
        client.table('api_call_logs').select('id').limit(1).execute()
        print("✓ Tabela api_call_logs: OK")
    except Exception as e:
        print(f"✗ Tabela api_call_logs: ERRO - {e}")
        tables_ok = False
    
    if tables_ok:
        print("\n" + "="*70)
        print("✅ TODAS AS TABELAS CONFIGURADAS COM SUCESSO!")
        print("="*70 + "\n")
        return True
    else:
        print("\n" + "="*70)
        print("⚠️  ALGUMAS TABELAS NÃO FORAM CRIADAS")
        print("="*70)
        print("\nExecute o SQL manualmente no Supabase SQL Editor\n")
        return False


if __name__ == "__main__":
    try:
        success = setup_tables()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ ERRO: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
