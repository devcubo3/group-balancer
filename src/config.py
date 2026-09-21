"""
Configurações do sistema carregadas das variáveis de ambiente.
"""
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Configurações da aplicação"""

    # Supabase
    supabase_url: str = Field(..., alias="SUPABASE_URL")
    # DEVE continuar sendo a chave ANON: painel_web.py a injeta no HTML servido
    # ao navegador. Trocar por uma service key aqui entregaria o banco inteiro a
    # quem abrisse o DevTools no painel.
    supabase_key: str = Field(..., alias="SUPABASE_KEY")

    # Chave de serviço, usada SÓ pelo rastreio de membros (src/membros.py):
    # grupo_membros e grupo_eventos guardam telefone de gente real e ficam com
    # RLS ligada e sem policy de leitura, justamente para a chave anon — que
    # está publicada no JS da landing page — não conseguir lê-las.
    # Vazia: o rastreio fica desligado e o resto do monitor segue igual.
    supabase_service_key: str = Field("", alias="SUPABASE_SERVICE_KEY")

    # WhatsApp API (UazAPI)
    # whatsapp_api_token DEVE ser o token da INSTÂNCIA, não o da conta UazAPI:
    # ele vai no header `token` das chamadas /group/*, e o token da conta é
    # recusado com HTTP 401 "Invalid token".
    whatsapp_api_url: str = Field("https://free.uazapi.com", alias="WHATSAPP_API_URL")
    whatsapp_api_token: str = Field("c11bf8be-2373-4904-aa3f-baefcfc16614", alias="WHATSAPP_API_TOKEN")
    whatsapp_admin_number: str = Field("553391269004", alias="WHATSAPP_ADMIN_NUMBER")
    
    # WhatsApp Group Settings
    group_description: str = Field("Grupo oficial - Bem-vindo!", alias="GROUP_DESCRIPTION")
    group_image_url: str = Field("", alias="GROUP_IMAGE_URL")  # URL da imagem do grupo

    # Business Rules
    max_members_for_redirect: int = Field(900, alias="MAX_MEMBERS_FOR_REDIRECT")
    scale_out_threshold: int = Field(950, alias="SCALE_OUT_THRESHOLD")
    whatsapp_max_capacity: int = Field(1000, alias="WHATSAPP_MAX_CAPACITY")

    # Circuit breaker: um nicho não ganha dois grupos dentro desta janela.
    # Um grupo leva semanas para encher 950 membros, então qualquer criação em
    # sequência é bug, não demanda. Em 2026-09-12 uma falha de leitura criou 8
    # grupos em 9h; com este limite teriam sido no máximo 9 — e, com o guard de
    # dupla confirmação, nenhum. É a rede de segurança, não a correção.
    group_create_cooldown_minutes: int = Field(60, alias="GROUP_CREATE_COOLDOWN_MINUTES")

    # Monitor Configuration
    monitor_check_interval: int = Field(60, alias="MONITOR_CHECK_INTERVAL")
    daily_sync_interval: int = Field(24, alias="DAILY_SYNC_INTERVAL")
    api_call_delay: int = Field(2, alias="API_CALL_DELAY")
    api_timeout: int = Field(30, alias="API_TIMEOUT")
    daily_monitor_test_interval: int = Field(3, alias="DAILY_MONITOR_TEST_INTERVAL")

    # Rastreio de membros e atribuição de anúncio
    # ------------------------------------------------------------------
    # O grupo mais novo de cada nicho tem o roster conferido a cada ciclo (é
    # para onde a landing manda o tráfego pago). Os demais, só neste intervalo:
    # saída em grupo antigo não tem pressa, mas invisível ela não pode ficar.
    roster_interval_min: int = Field(5, alias="ROSTER_INTERVAL_MIN")
    # Quanto tempo um clique na landing continua elegível para casar com uma
    # entrada no grupo. Curto demais perde quem demora a tocar em "entrar";
    # longo demais casa gente com anúncio que não foi o dela.
    atribuicao_janela_min: int = Field(30, alias="ATRIBUICAO_JANELA_MIN")

    # Painel de grupos (servido pelo proprio processo do monitor)
    painel_port: int = Field(8080, alias="PAINEL_PORT")
    # Vazio = painel aberto a quem tiver a URL. Preenchido, exige ?t=<token>.
    painel_token: str = Field("", alias="PAINEL_TOKEN")

    # Logging
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    log_file: str = Field("logs/monitor.log", alias="LOG_FILE")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


# Instância global de configurações
settings = Settings()
