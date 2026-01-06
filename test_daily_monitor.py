"""
Monitor Diário em LOOP - Versão para Testes
=============================================

ATENÇÃO: Este é um modo de TESTE para acompanhar o monitoramento em tempo real.
Para produção, use daily_monitor.py agendado 1x por dia.

Este script executa o monitoramento de TODOS os grupos em LOOP com intervalo configurável.

Uso:
----
# Com intervalo padrão (3 minutos)
python test_daily_monitor.py

# Com intervalo customizado (em minutos)
python test_daily_monitor.py --interval 5

Configurações no .env:
----------------------
DAILY_MONITOR_TEST_INTERVAL=3  # Intervalo em MINUTOS (padrão: 3)

O que faz:
----------
1. Executa monitoramento completo de TODOS os grupos
2. Aguarda X minutos (configurável)
3. Repete o processo
4. Continua rodando até Ctrl+C
"""

import sys
import logging
import time
import argparse
from datetime import datetime, timedelta

from src.monitor import GroupMonitor, setup_logging
from src.config import settings


class TestDailyMonitor:
    """
    Monitor diário em loop para testes e acompanhamento em tempo real.
    """

    def __init__(self, interval_minutes: int = 3):
        self.monitor = GroupMonitor()
        self.interval_minutes = interval_minutes
        self.interval_seconds = interval_minutes * 60
        self.is_running = False
        self.execution_count = 0

    def run(self):
        """
        Executa o monitor diário em loop contínuo.
        """
        logger = logging.getLogger(__name__)

        logger.info("\n" + "🧪" * 40)
        logger.info("🧪 MONITOR DIÁRIO EM LOOP - MODO TESTE")
        logger.info("🧪" * 40)
        logger.info(f"⏱️  Intervalo: {self.interval_minutes} minutos ({self.interval_seconds}s)")
        logger.info(f"🎯 Monitora: TODOS os grupos ativos")
        logger.info(f"🔄 Modo: Loop contínuo (Ctrl+C para parar)")
        logger.info("🧪" * 40 + "\n")

        self.is_running = True

        try:
            while self.is_running:
                self.execution_count += 1
                
                logger.info("\n" + "=" * 80)
                logger.info(f"🔄 EXECUÇÃO #{self.execution_count}")
                logger.info(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info("=" * 80 + "\n")

                # Executa o monitoramento completo
                try:
                    self.monitor.daily_full_group_check()
                except Exception as e:
                    logger.error(f"✗ Erro durante monitoramento: {e}", exc_info=True)

                # Calcula próxima execução
                next_run = datetime.now() + timedelta(minutes=self.interval_minutes)
                
                logger.info("\n" + "-" * 80)
                logger.info(f"✅ Execução #{self.execution_count} concluída!")
                logger.info(f"⏳ Próxima execução em {self.interval_minutes} minutos")
                logger.info(f"🕐 Próximo horário: {next_run.strftime('%H:%M:%S')}")
                logger.info(f"⏹️  Pressione Ctrl+C para parar")
                logger.info("-" * 80 + "\n")

                # Aguarda o intervalo com contador regressivo
                self._wait_with_countdown(self.interval_seconds)

        except KeyboardInterrupt:
            logger.info("\n\n" + "⚠️ " * 40)
            logger.info("⚠️  INTERRUPÇÃO PELO USUÁRIO (Ctrl+C)")
            logger.info("⚠️ " * 40)
            logger.info(f"📊 Total de execuções: {self.execution_count}")
            logger.info("🛑 Encerrando monitor de testes...\n")
            self.stop()

        except Exception as e:
            logger.error(f"\n✗ ERRO CRÍTICO: {e}", exc_info=True)
            logger.info(f"📊 Execuções completadas antes do erro: {self.execution_count}\n")
            self.stop()

    def _wait_with_countdown(self, seconds: int):
        """
        Aguarda o intervalo mostrando contador regressivo a cada 30 segundos.
        
        Args:
            seconds: Segundos para aguardar
        """
        logger = logging.getLogger(__name__)
        
        remaining = seconds
        intervals = [180, 120, 60, 30, 10]  # Marcos para mostrar tempo restante
        
        while remaining > 0 and self.is_running:
            # Mostra tempo restante em marcos específicos
            if remaining in intervals:
                minutes = remaining // 60
                secs = remaining % 60
                if minutes > 0:
                    logger.info(f"⏳ Aguardando... {minutes}min {secs}s restantes")
                else:
                    logger.info(f"⏳ Aguardando... {secs}s restantes")
            
            time.sleep(1)
            remaining -= 1

    def stop(self):
        """
        Para a execução do monitor.
        """
        self.is_running = False


def parse_args():
    """
    Processa argumentos da linha de comando.
    """
    parser = argparse.ArgumentParser(
        description='Monitor Diário em Loop - Modo de Teste',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python test_daily_monitor.py              # Intervalo padrão (3 min)
  python test_daily_monitor.py --interval 5 # Intervalo de 5 minutos
  python test_daily_monitor.py -i 1         # Intervalo de 1 minuto (teste rápido)
        """
    )
    
    parser.add_argument(
        '-i', '--interval',
        type=int,
        default=3,
        help='Intervalo entre execuções em MINUTOS (padrão: 3)'
    )
    
    return parser.parse_args()


def main():
    """
    Ponto de entrada do monitor de testes.
    """
    # Processa argumentos
    args = parse_args()
    
    # Configura logging
    setup_logging()
    logger = logging.getLogger(__name__)

    # Validação
    if args.interval < 1:
        logger.error("❌ Intervalo deve ser pelo menos 1 minuto!")
        return 1
    
    if args.interval > 60:
        logger.warning(f"⚠️  Intervalo de {args.interval} minutos é muito longo para teste!")
        logger.warning("⚠️  Considere usar daily_monitor.py agendado ao invés disso.")
        response = input("\n   Continuar mesmo assim? (s/N): ")
        if response.lower() != 's':
            logger.info("❌ Cancelado pelo usuário")
            return 1

    try:
        monitor = TestDailyMonitor(interval_minutes=args.interval)
        monitor.run()
        return 0

    except Exception as e:
        logger.error(f"✗ ERRO CRÍTICO: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
