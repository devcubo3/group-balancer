"""
Monitor Diário de Todos os Grupos
====================================

Este script executa o monitoramento diário completo de TODOS os grupos ativos.

Diferenças do monitor principal (main.py):
- main.py: Monitora o grupo MAIS NOVO continuamente (a cada 60s)
- daily_monitor.py: Monitora TODOS os grupos uma vez por dia

Funcionalidades:
1. Busca todos os grupos ativos do Supabase
2. Sincroniza a contagem de membros de cada grupo com a API
3. Aguarda delay entre cada chamada (evitar rate limit)
4. Salva logs detalhados no banco de dados
5. Permite balanceamento global (não deixa grupos para trás)

Uso:
----
# Execução única (manual):
python daily_monitor.py

# Agendar execução diária (Windows Task Scheduler):
# Criar tarefa agendada para executar este script 1x por dia

# Agendar execução diária (Linux cron):
# 0 3 * * * cd /caminho/projeto && python daily_monitor.py

Configurações:
--------------
As configurações são lidas do arquivo .env:
- API_CALL_DELAY: Segundos de espera entre cada chamada (padrão: 2s)
- API_TIMEOUT: Timeout para chamadas da API (padrão: 30s)
"""

import sys
import logging
from datetime import datetime

# Importa o monitor
from src.monitor import GroupMonitor, setup_logging


def main():
    """
    Executa o monitoramento diário completo de todos os grupos.
    """
    # Configura logging
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("\n" + "=" * 80)
    logger.info("🌍 MONITOR DIÁRIO DE TODOS OS GRUPOS")
    logger.info("=" * 80)
    logger.info(f"📅 Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"🎯 Objetivo: Sincronizar TODOS os grupos ativos com a API")
    logger.info("=" * 80 + "\n")

    try:
        # Cria instância do monitor
        monitor = GroupMonitor()

        # Executa monitoramento diário completo
        monitor.daily_full_group_check()

        logger.info("\n" + "=" * 80)
        logger.info("✅ MONITORAMENTO DIÁRIO CONCLUÍDO COM SUCESSO!")
        logger.info("=" * 80 + "\n")

        return 0

    except KeyboardInterrupt:
        logger.info("\n⚠ Interrupção pelo usuário (Ctrl+C)")
        return 1

    except Exception as e:
        logger.error(f"\n✗ ERRO CRÍTICO no monitoramento diário: {e}", exc_info=True)
        logger.info("=" * 80 + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
