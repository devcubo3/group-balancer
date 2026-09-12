"""
Monitor de grupos - Verificação em tempo real e sincronização a cada 12 horas.
"""
import logging
import time
import schedule
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from .config import settings
from .load_balancer import LoadBalancer
from .models import MonitorLog, WhatsAppGroup

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
        Verifica o grupo mais recente de CADA nicho e cria novo se necessário.

        Cada nicho tem sua própria cadeia de overflow, então o scale-out é
        avaliado nicho a nicho — um processo só atende todos eles, para que um
        nicho novo seja uma linha em tabela e não um deploy novo.
        """
        logger.info("=" * 60)
        logger.info(f"🔍 VERIFICAÇÃO AUTOMÁTICA - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)

        try:
            nichos = self.load_balancer.db.get_active_nichos()
        except Exception as e:
            # Pular o ciclo é o comportamento certo: sem a lista de nichos não
            # há decisão segura a tomar. Só não pode passar em branco.
            logger.error(f"✗ Falha ao buscar nichos ativos, ciclo abortado: {e}", exc_info=True)
            self.load_balancer.db.save_monitor_log(MonitorLog(
                monitor_type="newest_group",
                status_message="Ciclo abortado: falha ao buscar nichos ativos",
                has_error=True,
                error_message=str(e),
            ))
            return

        if not nichos:
            logger.warning("⚠ Nenhum nicho ativo cadastrado — nada a monitorar")
            return

        for nicho in nichos:
            try:
                self._check_nicho(nicho)
            except Exception as e:
                logger.error(f"✗ Erro ao verificar nicho {nicho.slug}: {e}", exc_info=True)

    def _bloqueio_por_cooldown(self, stats: dict) -> Optional[str]:
        """
        Motivo do bloqueio se o nicho já ganhou um grupo há pouco, senão None.

        Um grupo leva semanas para encher, então dois nascimentos seguidos são
        sempre bug. É a rede de segurança por trás dos guards, não a correção.
        """
        ultimo = stats.get("ultimo_created_at")
        if not ultimo:
            return None

        cooldown = timedelta(minutes=settings.group_create_cooldown_minutes)
        idade = datetime.now(timezone.utc) - ultimo

        if idade >= cooldown:
            return None

        restante = int((cooldown - idade).total_seconds() // 60) + 1
        return (
            f"cooldown ativo — último grupo do nicho nasceu há "
            f"{int(idade.total_seconds() // 60)}min "
            f"(mínimo {settings.group_create_cooldown_minutes}min, faltam ~{restante}min)"
        )

    def _criar_grupo_do_nicho(
        self, nicho, motivo: str, exige_nicho_vazio: bool = False
    ) -> Tuple[Optional[WhatsAppGroup], str, Optional[str]]:
        """
        Caminho ÚNICO de criação de grupo do monitor.

        Concentra aqui os guards e a numeração porque antes os dois caminhos
        (primeiro grupo e scale-out) numeravam de jeitos diferentes — e o de
        primeiro grupo hardcodava `#001`, criando um segundo "#001" ao lado do
        "#023" que já existia.

        Args:
            motivo: aparece no log, distingue 'nicho sem grupo' de 'scale-out'
            exige_nicho_vazio: confirma, com uma segunda leitura independente,
                que o nicho realmente não tem grupo nenhum antes de criar

        Returns:
            (grupo_ou_None, status_message, error_message_ou_None)
        """
        stats = self.load_balancer.db.get_nicho_group_stats(nicho.id)

        # Guard de dupla confirmação: criar grupo é irreversível (nasce de
        # verdade no WhatsApp e passa a receber ofertas e leads), então as duas
        # leituras precisam concordar que o nicho está vazio.
        if exige_nicho_vazio and stats["total"] > 0:
            erro = (
                f"leitura inicial não viu grupo ativo em {nicho.slug}, mas a "
                f"confirmação encontrou {stats['total']} grupo(s) na cadeia"
            )
            logger.error(f"⛔ Criação abortada ({motivo}): {erro}")
            return None, f"Criação abortada: leituras divergentes ({motivo})", erro

        bloqueio = self._bloqueio_por_cooldown(stats)
        if bloqueio:
            logger.error(f"⛔ Criação barrada ({motivo}): {bloqueio}")
            return None, f"Criação barrada ({motivo})", bloqueio

        # Numeração continua de onde a cadeia parou, contando inclusive grupos
        # arquivados — o nome é a identidade do grupo na lista do WhatsApp e
        # repetir um número já usado confunde quem já está nos grupos.
        numero = stats["max_numero"] + 1
        nome = f"{nicho.prefixo_grupo()} #{numero:03d}"

        novo = self.load_balancer.create_new_group(
            group_number=numero, group_name=nome, nicho=nicho
        )

        if novo:
            logger.info(f"✅ NOVO GRUPO CRIADO: {novo.name}\n   Link: {novo.invite_link}")
            return novo, f"Grupo {nome} criado no nicho {nicho.slug} ({motivo})", None

        logger.error(f"✗ FALHA ao criar {nome} no nicho {nicho.slug}")
        return (
            None,
            f"Falha ao criar {nome} no nicho {nicho.slug} ({motivo})",
            "create_new_group retornou None — ver api_call_logs",
        )

    def _check_nicho(self, nicho):
        """
        Verifica a cadeia de grupos de um nicho e faz scale-out se necessário.

        Salva SEMPRE um log em monitor_logs, inclusive quando a verificação
        falha: antes o log dependia de ter lido um grupo, então uma falha de
        leitura não deixava rastro nenhum e o bug ficou horas invisível.
        """
        newest_group = None
        previous_count = None
        new_group_created = False
        new_group_id = None
        error_occurred = False
        error_msg = None
        status_message = None
        group_name = None

        try:
            logger.info(f"🏷️  Nicho: {nicho.nome} ({nicho.slug})")

            # Busca o grupo mais novo DO NICHO. Levanta se a consulta falhar —
            # None aqui significa exclusivamente "nicho sem grupo ativo".
            newest_group = self.load_balancer.db.get_newest_group(nicho.id)

            if not newest_group:
                logger.warning(f"⚠ Nicho {nicho.slug} sem grupo! Confirmando antes de criar...")

                novo, status_message, error_msg = self._criar_grupo_do_nicho(
                    nicho, motivo="nicho sem grupo", exige_nicho_vazio=True
                )
                # group_name guarda o nome de um grupo que existe. Se a criação
                # foi barrada, não existe nenhum — o motivo está no status_message.
                group_name = novo.name if novo else None
                new_group_created = novo is not None
                new_group_id = novo.group_id_api if novo else None
                error_occurred = error_msg is not None
                return

            previous_count = newest_group.member_count
            group_name = newest_group.name

            # Sincroniza a contagem de membros do grupo mais novo
            logger.info(f"📊 Verificando grupo: {newest_group.name}")
            self.load_balancer.sync_group_members(newest_group)

            # Busca novamente após sincronização
            newest_group = self.load_balancer.db.get_newest_group(nicho.id) or newest_group
            group_name = newest_group.name
            status_message = f"Verificação do grupo mais novo: {newest_group.member_count} membros"

            if self.load_balancer.should_scale_out(newest_group):
                logger.warning(
                    f"🚨 SCALE-OUT NECESSÁRIO!\n"
                    f"   Nicho: {nicho.nome}\n"
                    f"   Grupo atual: {newest_group.name}\n"
                    f"   Membros: {newest_group.member_count}\n"
                    f"   Threshold: {settings.scale_out_threshold}"
                )

                novo, status_message, error_msg = self._criar_grupo_do_nicho(
                    nicho, motivo="scale-out"
                )
                new_group_created = novo is not None
                new_group_id = novo.group_id_api if novo else None
                error_occurred = error_msg is not None

            else:
                logger.info(
                    f"✓ Sistema OK - {newest_group.name} "
                    f"({newest_group.member_count}/{settings.scale_out_threshold} membros)"
                )

        except Exception as e:
            error_occurred = True
            error_msg = str(e)
            status_message = f"Falha ao verificar o nicho {nicho.slug}"
            logger.error(f"✗ Erro na verificação do grupo mais novo: {e}", exc_info=True)

        finally:
            member_count = newest_group.member_count if newest_group else None
            log = MonitorLog(
                monitor_type="newest_group",
                group_id_api=newest_group.group_id_api if newest_group else None,
                group_name=group_name,
                member_count=member_count,
                previous_count=previous_count,
                count_difference=(
                    member_count - previous_count
                    if member_count is not None and previous_count is not None
                    else 0
                ),
                new_group_created=new_group_created,
                new_group_id_api=new_group_id,
                status_message=status_message or f"Ciclo do nicho {nicho.slug}",
                has_error=error_occurred,
                error_message=error_msg,
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
