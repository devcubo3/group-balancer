#!/usr/bin/env python3
"""
Script para criar o primeiro grupo "Dona Promo #001"
"""
import sys
from pathlib import Path

# Adiciona o diretório src ao path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.load_balancer import LoadBalancer
from src.monitor import setup_logging


def main():
    """Cria o grupo Dona Promo #001"""
    
    # Configura logging
    setup_logging()
    
    print("\n" + "="*60)
    print("CRIAÇÃO DO GRUPO 'DONA PROMO #001'")
    print("="*60 + "\n")
    
    # Inicializa o load balancer
    load_balancer = LoadBalancer()
    
    # Cria o grupo com nome customizado
    print("🔧 Criando grupo 'Dona Promo #001'...")
    print("⏳ Aguarde, isso pode levar alguns segundos...\n")
    
    new_group = load_balancer.create_new_group(
        group_number=1,
        group_name="Dona Promo #001"
    )
    
    if new_group:
        print("\n" + "="*60)
        print("✅ GRUPO CRIADO COM SUCESSO!")
        print("="*60)
        print(f"\n📋 Detalhes do Grupo:")
        print(f"   Nome: {new_group.name}")
        print(f"   ID (JID): {new_group.group_id_api}")
        print(f"   Link de Convite: {new_group.invite_link}")
        print(f"   Membros: {new_group.member_count}")
        print(f"   Ativo: {'Sim' if new_group.is_active else 'Não'}")
        
        if new_group.subject:
            print(f"   Assunto: {new_group.subject}")
        if new_group.owner_jid:
            print(f"   Dono: {new_group.owner_jid}")
            
        print("\n✓ Grupo salvo no Supabase com sucesso!")
        print("✓ Logs de API salvos no banco de dados!")
        print("\n" + "="*60 + "\n")
        
        return 0
    else:
        print("\n" + "="*60)
        print("✗ FALHA AO CRIAR GRUPO!")
        print("="*60)
        print("\nVerifique:")
        print("1. As configurações no arquivo .env")
        print("2. Se o token da API UAZAPI está correto")
        print("3. Se a instância do WhatsApp está conectada")
        print("4. Se o Supabase está acessível")
        print("\nVeja os logs acima para mais detalhes.\n")
        
        return 1


if __name__ == "__main__":
    sys.exit(main())
