"""
Monitor de grupos - Verificação em tempo real e sincronização a cada 12 horas.
"""
import logging
import time
import schedule
from datetime import datetime
from typing import Optional

from .config import settings
from .load_balancer import LoadBalancer
from .models import MonitorLog

logger = logging.getLogger(__name__)


class GroupMonitor:
    """
    Monitor responsável por:
    1. Verificar periodicamente o grupo mais novo (a cada 60s)
    2. Criar novo grupo quando atingir 900 membros
    3. Sincronizar todos os grupos a cada 12 horas
    4. Salvar logs de todas as verificações no banco
    """

    def __init__(self):
        self.load_balancer = LoadBalancer()
        self.check_interval = settings.monitor_check_interval
        self.is_running = False

    def check_newest_group(self):
        """
        Verifica o grupo mais recente e cria novo se necessário.
        Salva log da verificação no banco de dados.
        """
        newest_group = None
        previous_count = None
        new_group_created = False
        new_group_id = None
        error_occurred = False
        error_msg = None

        try:
            logger.info("=" * 60)
            logger.info(f"🔍 VERIFICAÇÃO AUTOMÁTICA - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 60)

            # Busca o grupo mais novo
            newest_group = self.load_balancer.db.get_newest_group()

            if not newest_group:
                logger.warning("⚠ Nenhum grupo encontrado! Criando o primeiro grupo...")

                new_group = self.load_balancer.create_new_group(
                    group_number=1,
                    group_name="Caramelo Ofertas #001"
                )
                if new_group:
                    new_group_created = True
                    new_group_id = new_group.group_id_api

                    # Salva log da criação do primeiro grupo
                    log = MonitorLog(
                        monitor_type="newest_group",
                        status_message="Primeiro grupo criado (nenhum grupo existia)",
                        new_group_created=True,
                        new_group_id_api=new_group_id,
                        has_error=False
                    )
                    self.load_balancer.db.save_monitor_log(log)
                return

            # Guarda contagem anterior
            previous_count = newest_group.member_count

            # Sincroniza a contagem de membros do grupo mais novo
            logger.info(f"📊 Verificando grupo: {newest_group.name}")
            self.load_balancer.sync_group_members(newest_group)

            # Busca novamente após sincronização
            newest_group = self.load_balancer.db.get_newest_group()
            current_count = newest_group.member_count if newest_group else 0
            count_diff = current_count - previous_count if previous_count is not None else 0

            # Verifica se precisa criar novo grupo
            if newest_group and self.load_balancer.should_scale_out(newest_group):
                logger.warning(
                    f"🚨 SCALE-OUT NECESSÁRIO!\n"
                    f"   Grupo atual: {newest_group.name}\n"
                    f"   Membros: {newest_group.member_count}\n"
                    f"   Threshold: {settings.scale_out_threshold}"
                )

                # Extrai o número do grupo atual para criar o próximo
                # Ex: "Caramelo Ofertas #001" -> 2 (próximo)
                import re
                match = re.search(r'#(\d+)', newest_group.name)
                if match:
                    current_number = int(match.group(1))
                    next_number = current_number + 1
                    next_group_name = f"Caramelo Ofertas #{next_number:03d}"
                else:
                    # Se não tiver padrão, usa contador simples
                    active_groups = self.load_balancer.db.get_active_groups()
                    next_number = len(active_groups) + 1
                    next_group_name = f"Caramelo Ofertas #{next_number:03d}"

                new_group = self.load_balancer.create_new_group(
                    group_number=next_number,
                    group_name=next_group_name
                )

                if new_group:
                    new_group_created = True
                    new_group_id = new_group.group_id_api
                    logger.info(
                        f"✅ NOVO GRUPO CRIADO: {new_group.name}\n"
                        f"   Link: {new_group.invite_link}"
                    )
                else:
                    error_occurred = True
                    error_msg = "Falha ao criar novo grupo via API"
                    logger.error("✗ FALHA ao criar novo grupo!")

            else:
                logger.info(
                    f"✓ Sistema OK - {newest_group.name} "
                    f"({newest_group.member_count}/{settings.scale_out_threshold} membros)"
                )

        except Exception as e:
            error_occurred = True
            error_msg = str(e)
            logger.error(f"✗ Erro na verificação do grupo mais novo: {e}", exc_info=True)

        finally:
            # Salva log da verificação
            if newest_group:
                log = MonitorLog(
                    monitor_type="newest_group",
                    group_id_api=newest_group.group_id_api,
                    group_name=newest_group.name,
                    member_count=newest_group.member_count,
                    previous_count=previous_count,
                    count_difference=newest_group.member_count - previous_count if previous_count else 0,
                    new_group_created=new_group_created,
                    new_group_id_api=new_group_id,
                    status_message=f"Verificação do grupo mais novo: {newest_group.member_count} membros",
                    has_error=error_occurred,
                    error_message=error_msg
                )
                self.load_balancer.db.save_monitor_log(log)

    def daily_sync(self):
        """
        Sincronização a cada 12 horas de todos os grupos.
        Salva log da sincronização no banco de dados.
        """
        error_occurred = False
        error_msg = None
        stats = {}

        try:
            logger.info("=" * 60)
            logger.info(f"📅 SINCRONIZAÇÃO COMPLETA - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 60)

            stats = self.load_balancer.sync_all_groups()

            logger.info(
                f"✅ Sincronização completa concluída!\n"
                f"   Total: {stats['total']} grupos\n"
                f"   Atualizados: {stats['success']}\n"
                f"   Sem alteração: {stats['unchanged']}\n"
                f"   Falhas: {stats['failed']}"
            )

        except Exception as e:
            error_occurred = True
            error_msg = str(e)
            logger.error(f"✗ Erro na sincronização completa: {e}", exc_info=True)

        finally:
            # Salva log da sincronização
            status_msg = (
                f"Sincronização completa: {stats.get('total', 0)} grupos | "
                f"Atualizados: {stats.get('success', 0)} | "
                f"Falhas: {stats.get('failed', 0)}"
            )

            log = MonitorLog(
                monitor_type="full_sync",
                status_message=status_msg,
                has_error=error_occurred,
                error_message=error_msg
            )
            self.load_balancer.db.save_monitor_log(log)

    def daily_full_group_check(self):
        """
        Monitoramento diário de TODOS os grupos.
        
        Este método:
        1. Busca TODOS os grupos ativos do Supabase
        2. Para cada grupo, sincroniza a contagem de membros com a API
        3. Aguarda o delay configurado entre cada chamada (evitar rate limit)
        4. Salva logs detalhados de cada grupo verificado
        
        Diferença do daily_sync:
        - Este é focado em atualizar TODOS os grupos de forma sistemática
        - Útil para manter dados atualizados mesmo de grupos antigos
        - Permite balanceamento global (não deixar grupos para trás)
        """
        error_occurred = False
        error_msg = None
        stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "unchanged": 0,
            "total_members": 0
        }

        try:
            logger.info("=" * 60)
            logger.info(f"🌍 MONITORAMENTO DIÁRIO COMPLETO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 60)

            # Busca TODOS os grupos ativos
            all_groups = self.load_balancer.db.get_active_groups()
            stats["total"] = len(all_groups)

            if not all_groups:
                logger.warning("⚠ Nenhum grupo ativo encontrado!")
                return

            logger.info(f"📊 Total de grupos a verificar: {stats['total']}")
            logger.info(f"⏱️ Delay entre chamadas: {settings.api_call_delay}s")
            logger.info("-" * 60)

            # Processa cada grupo individualmente
            for index, group in enumerate(all_groups, 1):
                try:
                    logger.info(f"\n[{index}/{stats['total']}] 🔍 Verificando: {group.name}")
                    logger.info(f"   ID API: {group.group_id_api}")
                    logger.info(f"   Membros atuais (banco): {group.member_count}")

                    # Guarda contagem anterior
                    old_count = group.member_count

                    # Sincroniza com a API
                    success = self.load_balancer.sync_group_members(group)

                    if success:
                        # Busca dados atualizados
                        updated_group = self.load_balancer.db.get_group_by_api_id(group.group_id_api)
                        
                        if updated_group:
                            new_count = updated_group.member_count
                            stats["total_members"] += new_count
                            
                            if new_count != old_count:
                                diff = new_count - old_count
                                stats["success"] += 1
                                logger.info(f"   ✅ ATUALIZADO: {old_count} → {new_count} ({diff:+d})")
                                
                                # Salva log individual da atualização
                                log = MonitorLog(
                                    monitor_type="daily_individual",
                                    group_id_api=group.group_id_api,
                                    group_name=group.name,
                                    member_count=new_count,
                                    previous_count=old_count,
                                    count_difference=diff,
                                    status_message=f"Grupo atualizado: {old_count} → {new_count}",
                                    has_error=False
                                )
                                self.load_balancer.db.save_monitor_log(log)
                            else:
                                stats["unchanged"] += 1
                                logger.info(f"   ✓ Sem alteração ({new_count} membros)")
                        else:
                            stats["unchanged"] += 1
                    else:
                        stats["failed"] += 1
                        logger.error(f"   ✗ Falha ao sincronizar")
                        
                        # Salva log de erro
                        log = MonitorLog(
                            monitor_type="daily_individual",
                            group_id_api=group.group_id_api,
                            group_name=group.name,
                            member_count=group.member_count,
                            status_message="Falha na sincronização",
                            has_error=True,
                            error_message="Erro ao buscar dados da API"
                        )
                        self.load_balancer.db.save_monitor_log(log)

                    # Aguarda delay antes da próxima chamada (evitar rate limit)
                    if index < stats["total"]:
                        logger.debug(f"   ⏳ Aguardando {settings.api_call_delay}s...")
                        time.sleep(settings.api_call_delay)

                except Exception as e:
                    stats["failed"] += 1
                    logger.error(f"   ✗ Erro ao processar grupo {group.name}: {e}")
                    continue

            # Resumo final
            logger.info("\n" + "=" * 60)
            logger.info("📊 RESUMO DO MONITORAMENTO DIÁRIO")
            logger.info("=" * 60)
            logger.info(f"   Total de grupos verificados: {stats['total']}")
            logger.info(f"   ✅ Atualizados: {stats['success']}")
            logger.info(f"   ✓ Sem alteração: {stats['unchanged']}")
            logger.info(f"   ✗ Falhas: {stats['failed']}")
            logger.info(f"   👥 Total de membros: {stats['total_members']}")
            logger.info("=" * 60)

        except Exception as e:
            error_occurred = True
            error_msg = str(e)
            logger.error(f"✗ Erro no monitoramento diário completo: {e}", exc_info=True)

        finally:
            # Salva log geral do monitoramento diário
            status_msg = (
                f"Monitoramento diário: {stats.get('total', 0)} grupos | "
                f"Atualizados: {stats.get('success', 0)} | "
                f"Sem alteração: {stats.get('unchanged', 0)} | "
                f"Falhas: {stats.get('failed', 0)} | "
                f"Total membros: {stats.get('total_members', 0)}"
            )

            log = MonitorLog(
                monitor_type="daily_full_check",
                status_message=status_msg,
                has_error=error_occurred,
                error_message=error_msg
            )
            self.load_balancer.db.save_monitor_log(log)

    def run_continuous(self):
        """
        Executa o monitor em modo contínuo (loop infinito).
        """
        logger.info("🚀 MONITOR DE GRUPOS INICIADO")
        logger.info(f"   Intervalo de verificação: {self.check_interval}s")
        logger.info(f"   Sincronização completa: {settings.daily_sync_interval}h")
        logger.info(f"   Threshold para criar novo grupo: {settings.scale_out_threshold} membros")
        logger.info(f"   Limite máximo para redirect: {settings.max_members_for_redirect} membros")
        logger.info("=" * 60)

        self.is_running = True

        # Agenda sincronização a cada 12 horas
        schedule.every(settings.daily_sync_interval).hours.do(self.daily_sync)

        # Executa primeira verificação imediatamente
        self.check_newest_group()

        # Loop principal
        while self.is_running:
            try:
                # Executa tarefas agendadas (sync a cada 12h)
                schedule.run_pending()

                # Aguarda intervalo configurado
                time.sleep(self.check_interval)

                # Verifica grupo mais novo
                self.check_newest_group()

            except KeyboardInterrupt:
                logger.info("\n⚠ Interrupção pelo usuário (Ctrl+C)")
                self.stop()
                break

            except Exception as e:
                logger.error(f"✗ Erro no loop principal: {e}", exc_info=True)
                logger.info(f"⏳ Aguardando {self.check_interval}s antes de tentar novamente...")
                time.sleep(self.check_interval)

    def stop(self):
        """
        Para a execução do monitor.
        """
        logger.info("🛑 Encerrando monitor...")
        self.is_running = False


def setup_logging():
    """
    Configura o sistema de logging.
    """
    import os

    # Cria diretório de logs se não existir
    log_dir = os.path.dirname(settings.log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Configura formatação
    log_format = "%(asctime)s [%(levelname)s] %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Configura handlers
    handlers = [
        logging.StreamHandler(),  # Console
    ]

    # Adiciona file handler se configurado
    if settings.log_file:
        handlers.append(
            logging.FileHandler(settings.log_file, encoding="utf-8")
        )

    # Configura logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format=log_format,
        datefmt=date_format,
        handlers=handlers
    )

    # Reduz verbosidade de bibliotecas externas
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("supabase").setLevel(logging.WARNING)
