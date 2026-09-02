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
        choices=["monitor", "sync", "create-group", "get-best-group", "list-groups", "test"],
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

    parser.add_argument(
        "--nicho",
        type=str,
        help="Slug do nicho (ex: bebes, geral). Sem isso, opera em todos os nichos."
    )

    args = parser.parse_args()

    # Configura logging
    setup_logging()

    # Inicializa componentes
    monitor = GroupMonitor()
    load_balancer = LoadBalancer()

    # Resolve o nicho, se informado
    nicho = None
    if args.nicho:
        nicho = load_balancer.resolve_nicho(args.nicho)
        if not nicho:
            print(f"\n✗ Nicho '{args.nicho}' não encontrado ou inativo\n")
            sys.exit(1)
        print(f"\n🏷️  Nicho: {nicho.nome} ({nicho.slug})")

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
            new_group = load_balancer.create_new_group(group_number, group_name, nicho)

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

            result = load_balancer.get_best_group_for_lead(nicho.id if nicho else None)

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

        elif args.command == "list-groups":
            # Lista todos os grupos em que a instância do WhatsApp está.
            # É assim que se descobre o JID de um grupo-fonte recém-entrado,
            # para cadastrá-lo na tabela `fontes` apontando para um nicho.
            print("\n📋 Listando grupos da instância...\n")

            grupos = load_balancer.whatsapp.list_groups(force=True, no_participants=True)

            if not grupos:
                print("⚠ Nenhum grupo retornado. Verifique WHATSAPP_API_URL e WHATSAPP_API_TOKEN.\n")
                sys.exit(1)

            # JIDs já cadastrados, para saber o que falta registrar
            cadastrados = set()
            try:
                resp = load_balancer.db.client.table("fontes").select("chat_id").execute()
                cadastrados = {f["chat_id"] for f in (resp.data or [])}
            except Exception as e:
                print(f"(não foi possível ler `fontes`: {e})\n")

            print(f"{'JID':36} {'MEMBROS':>8}  {'FONTE?':8} NOME")
            print("-" * 100)
            for g in grupos:
                jid = g.get("JID") or g.get("jid") or g.get("id") or "?"
                nome = g.get("Name") or g.get("subject") or g.get("name") or "(sem nome)"
                membros = g.get("ParticipantCount") or len(g.get("Participants") or [])
                marca = "✓" if jid in cadastrados else "—"
                print(f"{jid:36} {membros:>8}  {marca:8} {nome}")

            print(f"\nTotal: {len(grupos)} grupo(s)\n")
            print("Para cadastrar um grupo como fonte de um nicho:")
            print("  INSERT INTO fontes (nicho_id, plataforma, chat_id, chat_title)")
            print("  VALUES ((SELECT id FROM nichos WHERE slug='bebes'),")
            print("          'whatsapp', '<JID>', '<nome do grupo>');\n")

        elif args.command == "test":
            # Testa conexões
            print("\n🧪 Testando conexões...\n")

            # Testa Supabase
            print("1️⃣ Testando conexão com Supabase...")
            groups = []
            try:
                nichos = load_balancer.db.get_active_nichos()
                print(f"   ✅ Conexão OK - {len(nichos)} nicho(s) ativo(s)")
                for n in nichos:
                    n_groups = load_balancer.db.get_active_groups(n.id)
                    print(f"      • {n.nome} ({n.slug}): {len(n_groups)} grupo(s)")
                    groups.extend(n_groups)
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
