#!/usr/bin/env python3
"""
Cria o primeiro grupo de um nicho.

Uso:
    python create_first_group.py --nicho bebes
    python create_first_group.py --nicho bebes --nome "Ofertas de Bebê #001"
"""
import argparse
import sys
from pathlib import Path

# Adiciona o diretório src ao path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.load_balancer import LoadBalancer
from src.monitor import setup_logging


def main():
    """Cria o primeiro grupo da cadeia de um nicho"""

    parser = argparse.ArgumentParser(description="Cria o primeiro grupo de um nicho")
    parser.add_argument("--nicho", required=True, help="Slug do nicho (ex: bebes)")
    parser.add_argument("--nome", help="Nome customizado do grupo")
    args = parser.parse_args()

    # Configura logging
    setup_logging()

    # Inicializa o load balancer
    load_balancer = LoadBalancer()

    nicho = load_balancer.resolve_nicho(args.nicho)
    if not nicho:
        print(f"\n✗ Nicho '{args.nicho}' não encontrado ou inativo\n")
        return 1

    group_name = args.nome or f"{nicho.prefixo_grupo()} #001"

    print("\n" + "="*60)
    print(f"CRIAÇÃO DO PRIMEIRO GRUPO — {nicho.nome}")
    print("="*60 + "\n")

    # Não recria a cadeia se ela já existe
    existentes = load_balancer.db.get_active_groups(nicho.id)
    if existentes:
        print(f"⚠ O nicho '{nicho.slug}' já tem {len(existentes)} grupo(s) ativo(s):")
        for g in existentes:
            print(f"   • {g.name} ({g.member_count} membros)")
        print("\nUse 'python main.py create-group --nicho "
              f"{nicho.slug}' para adicionar outro à cadeia.\n")
        return 1

    print(f"🔧 Criando grupo '{group_name}'...")
    print("⏳ Aguarde, isso pode levar alguns segundos...\n")

    new_group = load_balancer.create_new_group(
        group_number=1,
        group_name=group_name,
        nicho=nicho
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
