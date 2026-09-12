"""
Guards que impedem o monitor de criar grupo por engano.

Regressão do incidente de 2026-09-12: `get_newest_group` engolia o erro de
consulta e devolvia None, o monitor lia isso como "nicho sem grupo" e criava um
grupo novo. Em 9h nasceram 8 "#001" duplicados que passaram a receber ofertas e
a roubar todos os leads da landing page (que ordena por membros crescente).

Nada aqui toca Supabase ou UazAPI — o SupabaseClient é injetado mockado.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from postgrest.exceptions import APIError

from src.models import Nicho, WhatsAppGroup
from src.monitor import GroupMonitor
from src.supabase_client import parse_group_number


NICHO_GERAL = Nicho(
    id="c20b64d2-c0ea-40c9-b365-5219e7662c80",
    nome="Caramelo Ofertas",
    slug="geral",
    nome_grupo="Caramelo Ofertas",
)


def grupo(nome="Caramelo Ofertas #023", membros=47):
    return WhatsAppGroup(
        group_id_api="120363424758157492@g.us",
        name=nome,
        invite_link="https://chat.whatsapp.com/abc",
        member_count=membros,
        subject=nome,
        nicho_id=NICHO_GERAL.id,
    )


def stats(total=1, max_numero=23, idade_minutos=None):
    """Retorno de get_nicho_group_stats. idade_minutos=None => sem grupo recente."""
    ultimo = None
    if idade_minutos is not None:
        ultimo = datetime.now(timezone.utc) - timedelta(minutes=idade_minutos)
    return {"total": total, "max_numero": max_numero, "ultimo_created_at": ultimo}


@pytest.fixture
def monitor():
    """GroupMonitor com LoadBalancer mockado — sem rede, sem env de produção."""
    m = GroupMonitor.__new__(GroupMonitor)
    m.load_balancer = MagicMock()
    m.load_balancer.db = MagicMock()
    m.check_interval = 60
    m.is_running = False
    return m


def log_salvo(monitor):
    """O MonitorLog gravado no ciclo."""
    monitor.load_balancer.db.save_monitor_log.assert_called_once()
    return monitor.load_balancer.db.save_monitor_log.call_args[0][0]


# --- o bug original -------------------------------------------------------


def test_falha_de_leitura_nao_cria_grupo(monitor):
    """Consulta que falha não pode virar 'nicho sem grupo'."""
    monitor.load_balancer.db.get_newest_group.side_effect = APIError(
        {"message": "connection timeout", "code": "500"}
    )

    monitor._check_nicho(NICHO_GERAL)

    monitor.load_balancer.create_new_group.assert_not_called()


def test_falha_de_leitura_deixa_rastro_no_monitor_logs(monitor):
    """Antes o log dependia de ter lido um grupo: a falha sumia sem rastro."""
    monitor.load_balancer.db.get_newest_group.side_effect = APIError(
        {"message": "connection timeout", "code": "500"}
    )

    monitor._check_nicho(NICHO_GERAL)

    log = log_salvo(monitor)
    assert log.has_error is True
    assert "connection timeout" in log.error_message
    assert log.new_group_created is False


def test_leituras_divergentes_abortam_criacao(monitor):
    """Primeira leitura diz vazio, confirmação acha 1 grupo: não cria."""
    monitor.load_balancer.db.get_newest_group.return_value = None
    monitor.load_balancer.db.get_nicho_group_stats.return_value = stats(
        total=1, max_numero=23
    )

    monitor._check_nicho(NICHO_GERAL)

    monitor.load_balancer.create_new_group.assert_not_called()
    log = log_salvo(monitor)
    assert log.has_error is True
    assert "confirmação encontrou 1 grupo" in log.error_message


# --- cooldown -------------------------------------------------------------


def test_cooldown_bloqueia_grupo_recem_criado(monitor):
    """Dois grupos em menos de 1h é bug — um grupo leva semanas para encher."""
    monitor.load_balancer.db.get_newest_group.return_value = grupo(membros=960)
    monitor.load_balancer.should_scale_out.return_value = True
    monitor.load_balancer.db.get_nicho_group_stats.return_value = stats(
        total=1, max_numero=23, idade_minutos=10
    )

    monitor._check_nicho(NICHO_GERAL)

    monitor.load_balancer.create_new_group.assert_not_called()
    assert "cooldown ativo" in log_salvo(monitor).error_message


def test_scale_out_legitimo_passa_apos_o_cooldown(monitor):
    """Cooldown é rede de segurança, não pode travar o scale-out de verdade."""
    monitor.load_balancer.db.get_newest_group.return_value = grupo(membros=960)
    monitor.load_balancer.should_scale_out.return_value = True
    monitor.load_balancer.db.get_nicho_group_stats.return_value = stats(
        total=1, max_numero=23, idade_minutos=60 * 24 * 30
    )
    monitor.load_balancer.create_new_group.return_value = grupo(
        nome="Caramelo Ofertas #024", membros=1
    )

    monitor._check_nicho(NICHO_GERAL)

    monitor.load_balancer.create_new_group.assert_called_once()
    assert log_salvo(monitor).new_group_created is True


# --- numeração ------------------------------------------------------------


def test_numeracao_continua_da_cadeia(monitor):
    """A cadeia do geral vai em #023: o próximo é #024, nunca outro #001."""
    monitor.load_balancer.db.get_newest_group.return_value = grupo(membros=960)
    monitor.load_balancer.should_scale_out.return_value = True
    monitor.load_balancer.db.get_nicho_group_stats.return_value = stats(
        total=1, max_numero=23, idade_minutos=60 * 24 * 30
    )
    monitor.load_balancer.create_new_group.return_value = grupo(
        nome="Caramelo Ofertas #024"
    )

    monitor._check_nicho(NICHO_GERAL)

    assert (
        monitor.load_balancer.create_new_group.call_args.kwargs["group_name"]
        == "Caramelo Ofertas #024"
    )


def test_nicho_de_fato_vazio_ganha_o_001(monitor):
    """O caminho legítimo continua funcionando: nicho novo nasce com #001."""
    monitor.load_balancer.db.get_newest_group.return_value = None
    monitor.load_balancer.db.get_nicho_group_stats.return_value = stats(
        total=0, max_numero=0
    )
    monitor.load_balancer.create_new_group.return_value = grupo(
        nome="Caramelo Ofertas #001", membros=1
    )

    monitor._check_nicho(NICHO_GERAL)

    assert (
        monitor.load_balancer.create_new_group.call_args.kwargs["group_name"]
        == "Caramelo Ofertas #001"
    )
    assert log_salvo(monitor).new_group_created is True


@pytest.mark.parametrize(
    "nome, esperado",
    [
        ("Caramelo Ofertas #023", 23),
        ("Mãe Inteligente #001", 1),
        ("PromoBaby #007", 7),
        ("Grupo sem número", None),
        (None, None),
        ("", None),
    ],
)
def test_parse_group_number(nome, esperado):
    assert parse_group_number(nome) == esperado


# --- caminho feliz --------------------------------------------------------


def test_ciclo_normal_nao_cria_nada_e_loga(monitor):
    monitor.load_balancer.db.get_newest_group.return_value = grupo(membros=47)
    monitor.load_balancer.should_scale_out.return_value = False

    monitor._check_nicho(NICHO_GERAL)

    monitor.load_balancer.create_new_group.assert_not_called()
    log = log_salvo(monitor)
    assert log.has_error is False
    assert log.member_count == 47
