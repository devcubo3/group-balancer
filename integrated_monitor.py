"""
Monitor Integrado - Monitora grupo mais novo + Todos os grupos
================================================================

Este é um exemplo OPCIONAL de como integrar os dois monitores em um único processo.

Diferença dos scripts separados:
- main.py: Monitora apenas o grupo mais novo (a cada 60s)
- daily_monitor.py: Monitora todos os grupos (execução única)
- integrated_monitor.py: Faz AMBOS em um único processo

Como funciona:
1. Monitor contínuo do grupo mais novo (a cada 60s)
2. Monitoramento diário completo (agendado para às 3h da manhã)

Uso:
----
python integrated_monitor.py

Configurações (no .env):
------------------------
MONITOR_CHECK_INTERVAL=60        # Intervalo do monitor principal (segundos)
DAILY_MONITOR_TIME="03:00"       # Horário do monitoramento diário (HH:MM)
API_CALL_DELAY=2                 # Delay entre chamadas da API
"""

import sys
import logging
import schedule
import time
from datetime import datetime

from src.monitor import GroupMonitor, setup_logging
from src.config import settings


class IntegratedMonitor:
    """
    Monitor integrado que combina:
    1. Verificação contínua do grupo mais novo
    2. Monitoramento diário de todos os grupos
    """

    def __init__(self):
        self.monitor = GroupMonitor()
        self.is_running = False

        # Horário padrão para monitoramento diário (pode ser configurado no .env)
        self.daily_monitor_time = "03:00"  # 3h da manhã

    def run(self):
        """
        Executa o monitor integrado.
        """
        logger = logging.getLogger(__name__)

        logger.info("=" * 80)
        logger.info("🚀 MONITOR INTEGRADO DE GRUPOS INICIADO")
        logger.info("=" * 80)
        logger.info(f"   ⚡ Monitor contínuo: A cada {settings.monitor_check_interval}s")
        logger.info(f"   🌍 Monitor diário: {self.daily_monitor_time} (todos os grupos)")
        logger.info(f"   🔧 Threshold criar grupo: {settings.scale_out_threshold} membros")
        logger.info(f"   📊 Delay entre chamadas: {settings.api_call_delay}s")
        logger.info("=" * 80 + "\n")

        self.is_running = True

        # Agenda monitoramento diário às 3h da manhã
        schedule.every().day.at(self.daily_monitor_time).do(self._run_daily_monitor)

        # Agenda sincronização completa a cada 12h (do monitor original)
        schedule.every(settings.daily_sync_interval).hours.do(self.monitor.daily_sync)

        # Executa primeira verificação do grupo mais novo
        self.monitor.check_newest_group()

        logger.info("✅ Agendamentos configurados. Iniciando loop principal...\n")

        # Loop principal
        while self.is_running:
            try:
                # Executa tarefas agendadas (daily monitor + sync)
                schedule.run_pending()

                # Aguarda intervalo configurado
                time.sleep(settings.monitor_check_interval)

                # Verifica grupo mais novo
                self.monitor.check_newest_group()

            except KeyboardInterrupt:
                logger.info("\n⚠ Interrupção pelo usuário (Ctrl+C)")
                self.stop()
                break

            except Exception as e:
                logger.error(f"✗ Erro no loop principal: {e}", exc_info=True)
                logger.info(f"⏳ Aguardando {settings.monitor_check_interval}s antes de tentar novamente...")
                time.sleep(settings.monitor_check_interval)

    def _run_daily_monitor(self):
        """
        Executa o monitoramento diário completo.
        Chamado automaticamente pelo schedule às 3h da manhã.
        """
        logger = logging.getLogger(__name__)
        logger.info("\n" + "🌅" * 40)
        logger.info("⏰ HORÁRIO DO MONITORAMENTO DIÁRIO!")
        logger.info("🌅" * 40 + "\n")

        self.monitor.daily_full_group_check()

    def stop(self):
        """
        Para a execução do monitor.
        """
        logger = logging.getLogger(__name__)
        logger.info("🛑 Encerrando monitor integrado...")
        self.is_running = False


def main():
    """
    Ponto de entrada do monitor integrado.
    """
    # Configura logging
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        monitor = IntegratedMonitor()
        monitor.run()
        return 0

    except Exception as e:
        logger.error(f"✗ ERRO CRÍTICO: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
