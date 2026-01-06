#!/usr/bin/env python3
"""
WhatsApp Group Load Balancer & Auto-Scaling System
Script principal para execução do monitor.
"""
import argparse
import sys
from pathlib import Path

# Adiciona o diretório src ao path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.monitor import GroupMonitor, setup_logging
from src.load_balancer import LoadBalancer


def main():
    """Função principal"""

    parser = argparse.ArgumentParser(
        description="WhatsApp Group Load Balancer & Auto-Scaling System"
    )

    parser.add_argument(
        "command",
        choices=["monitor", "sync", "create-group", "get-best-group", "test"],
        help="Comando a ser executado"
    )

    parser.add_argument(
        "--group-name",
        type=str,
        help="Nome do grupo a ser criado (usado com create-group)"
    )

    parser.add_argument(
        "--group-number",
        type=int,
        help="Número do grupo a ser criado (usado com create-group)"
    )

    args = parser.parse_args()

    # Configura logging
    setup_logging()

    # Inicializa componentes
    monitor = GroupMonitor()
    load_balancer = LoadBalancer()

    try:
        if args.command == "monitor":
            # Executa monitor em loop contínuo
            print("\n🚀 Iniciando Monitor de Grupos...")
            print("   Pressione Ctrl+C para encerrar\n")
            monitor.run_continuous()

        elif args.command == "sync":
            # Executa sincronização manual
            print("\n🔄 Executando sincronização manual de todos os grupos...")
            stats = load_balancer.sync_all_groups()
            print(f"\n✅ Sincronização concluída!")
            print(f"   Total: {stats['total']} grupos")
            print(f"   Atualizados: {stats['success']}")
            print(f"   Sem alteração: {stats['unchanged']}")
            print(f"   Falhas: {stats['failed']}\n")

        elif args.command == "create-group":
            # Cria um novo grupo manualmente
            group_number = args.group_number
            group_name = args.group_name

            print(f"\n🔧 Criando novo grupo...")

            if group_name:
                print(f"   Nome customizado: {group_name}")
                new_group = load_balancer.create_new_group(group_number, group_name)
            else:
                new_group = load_balancer.create_new_group(group_number)

            if new_group:
                print(f"\n✅ Grupo criado com sucesso!")
                print(f"   Nome: {new_group.name}")
                print(f"   ID: {new_group.group_id_api}")
                print(f"   Link: {new_group.invite_link}\n")
            else:
                print("\n✗ Falha ao criar grupo!\n")
                sys.exit(1)

        elif args.command == "get-best-group":
            # Testa o algoritmo de load balancer
            print("\n🎯 Buscando melhor grupo para novo lead...")

            result = load_balancer.get_best_group_for_lead()

            if result.group:
                print(f"\n✅ Grupo encontrado!")
                print(f"   Nome: {result.group.name}")
                print(f"   Membros: {result.group.member_count}")
                print(f"   Link: {result.group.invite_link}")
                print(f"   Motivo: {result.reason}\n")
            else:
                print(f"\n⚠ Nenhum grupo disponível!")
                print(f"   Motivo: {result.reason}")
                print(f"   Criar novo grupo: {result.should_create_new}\n")

        elif args.command == "test":
            # Testa conexões
            print("\n🧪 Testando conexões...\n")

            # Testa Supabase
            print("1️⃣ Testando conexão com Supabase...")
            try:
                groups = load_balancer.db.get_active_groups()
                print(f"   ✅ Conexão OK - {len(groups)} grupos encontrados")
            except Exception as e:
                print(f"   ✗ Erro: {e}")

            # Testa WhatsApp API
            print("\n2️⃣ Testando conexão com WhatsApp API...")
            try:
                # Tenta buscar info de um grupo (se houver)
                if groups:
                    test_group = groups[0]
                    info = load_balancer.whatsapp.get_group_info(test_group.group_id_api)
                    if info:
                        print(f"   ✅ API OK - Grupo: {info.name}")
                    else:
                        print("   ⚠ API respondeu mas sem dados")
                else:
                    print("   ⚠ Sem grupos para testar API")
            except Exception as e:
                print(f"   ✗ Erro: {e}")

            print("\n✅ Testes concluídos!\n")

    except KeyboardInterrupt:
        print("\n\n⚠ Operação cancelada pelo usuário\n")
        sys.exit(0)

    except Exception as e:
        print(f"\n✗ Erro: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
