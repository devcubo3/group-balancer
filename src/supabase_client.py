"""
Cliente para interação com Supabase.
"""
import logging
from typing import List, Optional
from datetime import datetime

from supabase import create_client, Client
from postgrest.exceptions import APIError

from .config import settings
from .models import WhatsAppGroup, MonitorLog, ApiCallLog

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Cliente para gerenciar grupos no Supabase"""

    def __init__(self):
        self.client: Client = create_client(
            settings.supabase_url,
            settings.supabase_key
        )
        self.table_name = "controle_grupos"  # Nome real da tabela no Supabase

    def get_active_groups(self) -> List[WhatsAppGroup]:
        """
        Busca todos os grupos ativos ordenados por member_count (crescente).

        Returns:
            Lista de grupos ativos
        """
        try:
            response = (
                self.client.table(self.table_name)
                .select("*")
                .eq("status", "ativo")
                .order("membros_atuais", desc=False)
                .execute()
            )

            groups = []
            for db_data in response.data:
                mapped_data = {
                    "group_id_api": db_data.get("group_jid"),
                    "name": db_data.get("subject"),
                    "invite_link": db_data.get("link_convite", ""),
                    "member_count": db_data.get("membros_atuais", 0),
                    "is_active": db_data.get("status") == "ativo",
                    "created_at": db_data.get("created_at"),
                    "updated_at": db_data.get("created_at"),
                    "subject": db_data.get("subject"),
                    "description": db_data.get("description"),
                    "owner_jid": db_data.get("owner_jid"),
                    "created_timestamp": db_data.get("created_timestamp"),
                    "participant_version_id": db_data.get("participant_version_id"),
                    "is_announcement": db_data.get("is_announcement"),
                    "is_locked": db_data.get("is_locked"),
                    "is_parent": db_data.get("is_parent"),
                    "default_membership_approval_mode": db_data.get("default_membership_approval_mode"),
                    "is_incognito": db_data.get("is_incognito"),
                    "linked_parent_jid": db_data.get("linked_parent_jid"),
                }
                groups.append(WhatsAppGroup(**mapped_data))
            
            logger.info(f"✓ {len(groups)} grupos ativos encontrados no Supabase")
            return groups

        except APIError as e:
            logger.error(f"✗ Erro ao buscar grupos ativos: {e}")
            return []

    def get_newest_group(self) -> Optional[WhatsAppGroup]:
        """
        Busca o grupo mais recentemente criado (ativo).

        Returns:
            Grupo mais novo ou None
        """
        try:
            response = (
                self.client.table(self.table_name)
                .select("*")
                .eq("status", "ativo")
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )

            if response.data:
                db_data = response.data[0]
                mapped_data = {
                    "group_id_api": db_data.get("group_jid"),
                    "name": db_data.get("subject"),
                    "invite_link": db_data.get("link_convite"),
                    "member_count": db_data.get("membros_atuais", 0),
                    "is_active": db_data.get("status") == "ativo",
                    "created_at": db_data.get("created_at"),
                    "updated_at": db_data.get("created_at"),
                    "subject": db_data.get("subject"),
                    "description": db_data.get("description"),
                    "owner_jid": db_data.get("owner_jid"),
                    "created_timestamp": db_data.get("created_timestamp"),
                    "participant_version_id": db_data.get("participant_version_id"),
                    "is_announcement": db_data.get("is_announcement"),
                    "is_locked": db_data.get("is_locked"),
                    "is_parent": db_data.get("is_parent"),
                    "default_membership_approval_mode": db_data.get("default_membership_approval_mode"),
                    "is_incognito": db_data.get("is_incognito"),
                    "linked_parent_jid": db_data.get("linked_parent_jid"),
                }
                group = WhatsAppGroup(**mapped_data)
                logger.info(f"✓ Grupo mais novo: {group.name} ({group.member_count} membros)")
                return group

            logger.warning("⚠ Nenhum grupo ativo encontrado")
            return None

        except APIError as e:
            logger.error(f"✗ Erro ao buscar grupo mais novo: {e}")
            return None

    def get_best_group_for_redirect(self, max_members: int) -> Optional[WhatsAppGroup]:
        """
        Busca o grupo com menor número de membros que esteja abaixo do limite.

        Args:
            max_members: Limite máximo de membros para redirecionamento

        Returns:
            Melhor grupo para receber novo lead ou None
        """
        try:
            response = (
                self.client.table(self.table_name)
                .select("*")
                .eq("is_active", True)
                .lt("member_count", max_members)
                .order("member_count", desc=False)
                .limit(1)
                .execute()
            )

            if response.data:
                group = WhatsAppGroup(**response.data[0])
                logger.info(
                    f"✓ Melhor grupo para redirect: {group.name} "
                    f"({group.member_count}/{max_members} membros)"
                )
                return group

            logger.warning(f"⚠ Nenhum grupo disponível com menos de {max_members} membros")
            return None

        except APIError as e:
            logger.error(f"✗ Erro ao buscar melhor grupo: {e}")
            return None

    def create_group(self, group: WhatsAppGroup) -> Optional[WhatsAppGroup]:
        """
        Cria um novo grupo no banco de dados.

        Args:
            group: Dados do grupo a ser criado

        Returns:
            Grupo criado ou None em caso de erro
        """
        try:
            # Extrair número da instância do token ou URL
            instance_number = "553391269004"  # Número conectado na UAZAPI
            
            # Calcular ordem sequencial (próximo número disponível)
            count_response = self.client.table(self.table_name).select("id", count="exact").execute()
            ordem_sequencial = (count_response.count or 0) + 1
            
            data = {
                "instance_name": instance_number,
                "group_jid": group.group_id_api,
                "link_convite": group.invite_link,
                "membros_atuais": group.member_count,
                "capacidade_max": settings.whatsapp_max_capacity,
                "status": "ativo" if group.is_active else "arquivado",
                "ordem_sequencial": ordem_sequencial,
                # Campos adicionais da API UAZAPI
                "subject": group.subject,
                "description": group.description,
                "owner_jid": group.owner_jid,
                "created_timestamp": group.created_timestamp,
                "participant_version_id": group.participant_version_id,
                "is_announcement": group.is_announcement,
                "is_locked": group.is_locked,
                "is_parent": group.is_parent,
                "default_membership_approval_mode": group.default_membership_approval_mode,
                "is_incognito": group.is_incognito,
                "linked_parent_jid": group.linked_parent_jid,
            }

            response = self.client.table(self.table_name).insert(data).execute()

            if response.data:
                # Mapear os nomes de campos do Supabase para o modelo Pydantic
                db_data = response.data[0]
                mapped_data = {
                    "group_id_api": db_data.get("group_jid"),
                    "name": db_data.get("subject"),
                    "invite_link": db_data.get("link_convite"),
                    "member_count": db_data.get("membros_atuais", 0),
                    "is_active": db_data.get("status") == "ativo",
                    "created_at": db_data.get("created_at"),
                    "updated_at": db_data.get("updated_at"),
                    # Campos adicionais
                    "subject": db_data.get("subject"),
                    "description": db_data.get("description"),
                    "owner_jid": db_data.get("owner_jid"),
                    "created_timestamp": db_data.get("created_timestamp"),
                    "participant_version_id": db_data.get("participant_version_id"),
                    "is_announcement": db_data.get("is_announcement"),
                    "is_locked": db_data.get("is_locked"),
                    "is_parent": db_data.get("is_parent"),
                    "default_membership_approval_mode": db_data.get("default_membership_approval_mode"),
                    "is_incognito": db_data.get("is_incognito"),
                    "linked_parent_jid": db_data.get("linked_parent_jid"),
                }
                created_group = WhatsAppGroup(**mapped_data)
                logger.info(f"✓ Grupo criado no Supabase: {created_group.name}")
                return created_group

            logger.error("✗ Falha ao criar grupo: resposta vazia")
            return None

        except APIError as e:
            logger.error(f"✗ Erro ao criar grupo no Supabase: {e}")
            return None

    def update_member_count(self, group_id_api: str, new_count: int) -> bool:
        """
        Atualiza a contagem de membros de um grupo.

        Args:
            group_id_api: ID do grupo na API do WhatsApp
            new_count: Nova contagem de membros

        Returns:
            True se atualizado com sucesso, False caso contrário
        """
        try:
            response = (
                self.client.table(self.table_name)
                .update({
                    "membros_atuais": new_count
                })
                .eq("group_jid", group_id_api)
                .execute()
            )

            if response.data:
                logger.info(f"✓ Member count atualizado: {group_id_api} -> {new_count} membros")
                return True

            logger.warning(f"⚠ Grupo não encontrado para atualização: {group_id_api}")
            return False

        except APIError as e:
            logger.error(f"✗ Erro ao atualizar member_count: {e}")
            return False

    def deactivate_group(self, group_id_api: str) -> bool:
        """
        Marca um grupo como inativo.

        Args:
            group_id_api: ID do grupo na API do WhatsApp

        Returns:
            True se desativado com sucesso, False caso contrário
        """
        try:
            response = (
                self.client.table(self.table_name)
                .update({
                    "is_active": False,
                    "updated_at": datetime.utcnow().isoformat()
                })
                .eq("group_id_api", group_id_api)
                .execute()
            )

            if response.data:
                logger.info(f"✓ Grupo desativado: {group_id_api}")
                return True

            return False

        except APIError as e:
            logger.error(f"✗ Erro ao desativar grupo: {e}")
            return False

    def get_group_by_api_id(self, group_id_api: str) -> Optional[WhatsAppGroup]:
        """
        Busca um grupo pelo ID da API.

        Args:
            group_id_api: ID do grupo na API do WhatsApp

        Returns:
            Grupo encontrado ou None
        """
        try:
            response = (
                self.client.table(self.table_name)
                .select("*")
                .eq("group_jid", group_id_api)
                .limit(1)
                .execute()
            )

            if response.data:
                db_data = response.data[0]
                mapped_data = {
                    "group_id_api": db_data.get("group_jid"),
                    "name": db_data.get("subject"),
                    "invite_link": db_data.get("link_convite", ""),
                    "member_count": db_data.get("membros_atuais", 0),
                    "is_active": db_data.get("status") == "ativo",
                    "created_at": db_data.get("created_at"),
                    "updated_at": db_data.get("created_at"),
                    "subject": db_data.get("subject"),
                    "description": db_data.get("description"),
                    "owner_jid": db_data.get("owner_jid"),
                    "created_timestamp": db_data.get("created_timestamp"),
                    "participant_version_id": db_data.get("participant_version_id"),
                    "is_announcement": db_data.get("is_announcement"),
                    "is_locked": db_data.get("is_locked"),
                    "is_parent": db_data.get("is_parent"),
                    "default_membership_approval_mode": db_data.get("default_membership_approval_mode"),
                    "is_incognito": db_data.get("is_incognito"),
                    "linked_parent_jid": db_data.get("linked_parent_jid"),
                }
                return WhatsAppGroup(**mapped_data)

            return None

        except APIError as e:
            logger.error(f"✗ Erro ao buscar grupo por API ID: {e}")
            return None

    def save_monitor_log(self, log: MonitorLog) -> bool:
        """
        Salva um log de monitoramento no banco de dados.

        Args:
            log: Log a ser salvo

        Returns:
            True se salvo com sucesso, False caso contrário
        """
        try:
            data = {
                "monitor_type": log.monitor_type,
                "group_id_api": log.group_id_api,
                "group_name": log.group_name,
                "member_count": log.member_count,
                "previous_count": log.previous_count,
                "count_difference": log.count_difference,
                "new_group_created": log.new_group_created,
                "new_group_id_api": log.new_group_id_api,
                "status_message": log.status_message,
                "has_error": log.has_error,
                "error_message": log.error_message,
                "checked_at": datetime.utcnow().isoformat(),
            }

            response = self.client.table("monitor_logs").insert(data).execute()

            if response.data:
                logger.debug(f"✓ Log salvo: {log.monitor_type} - {log.status_message}")
                return True

            logger.warning("⚠ Falha ao salvar log: resposta vazia")
            return False

        except APIError as e:
            logger.error(f"✗ Erro ao salvar log de monitoramento: {e}")
            return False

    def get_recent_logs(self, monitor_type: Optional[str] = None, limit: int = 50) -> List[MonitorLog]:
        """
        Busca logs recentes de monitoramento.

        Args:
            monitor_type: Filtrar por tipo ('newest_group' ou 'full_sync'). None = todos
            limit: Quantidade de logs a retornar

        Returns:
            Lista de logs
        """
        try:
            query = self.client.table("monitor_logs").select("*")

            if monitor_type:
                query = query.eq("monitor_type", monitor_type)

            response = query.order("checked_at", desc=True).limit(limit).execute()

            logs = [MonitorLog(**log) for log in response.data]
            logger.debug(f"✓ {len(logs)} logs encontrados")
            return logs

        except APIError as e:
            logger.error(f"✗ Erro ao buscar logs: {e}")
            return []

    def save_api_call_log(self, log: ApiCallLog) -> bool:
        """
        Salva um log de chamada à API do WhatsApp.

        Args:
            log: Log da chamada API a ser salvo

        Returns:
            True se salvo com sucesso, False caso contrário
        """
        try:
            data = {
                "endpoint": log.endpoint,
                "method": log.method,
                "request_payload": log.request_payload,
                "response_data": log.response_data,
                "status_code": log.status_code,
                "success": log.success,
                "error_message": log.error_message,
                "duration_ms": log.duration_ms,
                "group_id_api": log.group_id_api,
                "called_at": (log.called_at or datetime.utcnow()).isoformat(),
            }

            response = self.client.table("api_call_logs").insert(data).execute()

            if response.data:
                logger.debug(f"✓ Log API salvo: {log.method} {log.endpoint} ({log.status_code})")
                return True

            logger.warning("⚠ Falha ao salvar log API: resposta vazia")
            return False

        except APIError as e:
            logger.error(f"✗ Erro ao salvar log de API: {e}")
            return False

    def save_api_call_logs_bulk(self, logs: List[ApiCallLog]) -> int:
        """
        Salva múltiplos logs de chamadas API de uma vez.

        Args:
            logs: Lista de logs a serem salvos

        Returns:
            Quantidade de logs salvos com sucesso
        """
        if not logs:
            return 0
            
        try:
            data_list = []
            for log in logs:
                data_list.append({
                    "service_name": "UAZAPI",  # Fixo pois usamos UAZAPI
                    "endpoint": log.endpoint,
                    "http_method": log.method,
                    "request_payload": log.request_payload,
                    "response_data": log.response_data,
                    "status_code": log.status_code,
                    "success": log.success,
                    "error_message": log.error_message,
                    "duration_ms": log.duration_ms,
                })

            response = self.client.table("api_call_logs").insert(data_list).execute()

            if response.data:
                count = len(response.data)
                logger.debug(f"✓ {count} logs de API salvos em lote")
                return count

            return 0

        except APIError as e:
            logger.error(f"✗ Erro ao salvar logs de API em lote: {e}")
            return 0

    def get_recent_api_logs(self, endpoint: Optional[str] = None, limit: int = 50) -> List[ApiCallLog]:
        """
        Busca logs recentes de chamadas à API.

        Args:
            endpoint: Filtrar por endpoint específico. None = todos
            limit: Quantidade de logs a retornar

        Returns:
            Lista de logs de API
        """
        try:
            query = self.client.table("api_call_logs").select("*")

            if endpoint:
                query = query.eq("endpoint", endpoint)

            response = query.order("called_at", desc=True).limit(limit).execute()

            logs = [ApiCallLog(**log) for log in response.data]
            logger.debug(f"✓ {len(logs)} logs de API encontrados")
            return logs

        except APIError as e:
            logger.error(f"✗ Erro ao buscar logs de API: {e}")
            return []
