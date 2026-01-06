"""
Configurações do sistema carregadas das variáveis de ambiente.
"""
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Configurações da aplicação"""

    # Supabase
    supabase_url: str = Field(..., alias="SUPABASE_URL")
    supabase_key: str = Field(..., alias="SUPABASE_KEY")

    # WhatsApp API
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

    # Monitor Configuration
    monitor_check_interval: int = Field(60, alias="MONITOR_CHECK_INTERVAL")
    daily_sync_interval: int = Field(24, alias="DAILY_SYNC_INTERVAL")
    api_call_delay: int = Field(2, alias="API_CALL_DELAY")
    api_timeout: int = Field(30, alias="API_TIMEOUT")
    daily_monitor_test_interval: int = Field(3, alias="DAILY_MONITOR_TEST_INTERVAL")

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
