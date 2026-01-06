"""
Serviço para interação com a API do WhatsApp (UAZAPI).

Documentação: https://docs.uazapi.com/tag/Grupos%20e%20Comunidades

Endpoints implementados baseados na documentação oficial da UAZAPI.
"""
import logging
import time
from typing import Optional, Dict, Any, List
from datetime import datetime

import httpx

from .config import settings
from .models import GroupInfoResponse, ApiCallLog

logger = logging.getLogger(__name__)


class WhatsAppService:
    """Cliente para a API UAZAPI do WhatsApp"""

    def __init__(self):
        self.base_url = settings.whatsapp_api_url
        self.token = settings.whatsapp_api_token
        self.admin_number = settings.whatsapp_admin_number
        self.timeout = settings.api_timeout

        # UAZAPI usa header 'token' ao invés de 'Authorization'
        self.headers = {
            "token": self.token,
            "Content-Type": "application/json"
        }
        
        self.api_logs = []  # Cache de logs para salvar depois

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        log_call: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Faz uma requisição à API do WhatsApp e registra o log.

        Args:
            method: Método HTTP (GET, POST, etc)
            endpoint: Endpoint da API
            data: Dados do body (para POST/PUT)
            params: Query parameters (para GET)
            log_call: Se deve registrar o log da chamada

        Returns:
            Resposta da API ou None em caso de erro
        """
        url = f"{self.base_url}{endpoint}"
        start_time = datetime.now()
        api_log = None
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                logger.debug(f"Fazendo requisição {method} para: {url}")

                response = client.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    json=data,
                    params=params
                )
                
                duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                logger.debug(f"Status Code: {response.status_code} ({duration_ms}ms)")

                response.raise_for_status()
                response_data = response.json()
                
                # Registra log de sucesso
                if log_call:
                    api_log = ApiCallLog(
                        endpoint=endpoint,
                        method=method,
                        request_payload=data,
                        response_data=response_data,
                        status_code=response.status_code,
                        success=True,
                        duration_ms=duration_ms,
                        called_at=start_time
                    )
                    self.api_logs.append(api_log)
                
                return response_data

        except httpx.HTTPStatusError as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            error_msg = f"Erro HTTP {e.response.status_code}: {e.response.text}"
            
            logger.error(
                f"✗ Erro HTTP na API WhatsApp: {e.response.status_code}\n"
                f"URL: {url}\n"
                f"Resposta: {e.response.text}"
            )
            
            # Registra log de erro
            if log_call:
                api_log = ApiCallLog(
                    endpoint=endpoint,
                    method=method,
                    request_payload=data,
                    response_data=None,
                    status_code=e.response.status_code,
                    success=False,
                    error_message=error_msg,
                    duration_ms=duration_ms,
                    called_at=start_time
                )
                self.api_logs.append(api_log)
            
            return None

        except httpx.RequestError as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            error_msg = f"Erro de conexão: {str(e)}"
            
            logger.error(f"✗ Erro de conexão com API WhatsApp: {e}")
            
            # Registra log de erro
            if log_call:
                api_log = ApiCallLog(
                    endpoint=endpoint,
                    method=method,
                    request_payload=data,
                    response_data=None,
                    status_code=None,
                    success=False,
                    error_message=error_msg,
                    duration_ms=duration_ms,
                    called_at=start_time
                )
                self.api_logs.append(api_log)
            
            return None

        except Exception as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            error_msg = f"Erro inesperado: {str(e)}"
            
            logger.error(f"✗ Erro inesperado na API WhatsApp: {e}")
            
            # Registra log de erro
            if log_call:
                api_log = ApiCallLog(
                    endpoint=endpoint,
                    method=method,
                    request_payload=data,
                    response_data=None,
                    status_code=None,
                    success=False,
                    error_message=error_msg,
                    duration_ms=duration_ms,
                    called_at=start_time
                )
                self.api_logs.append(api_log)
            
            return None

    def create_group(self, group_name: str, description: str = "", image_url: str = "") -> Optional[Dict[str, Any]]:
        """
        Cria um novo grupo no WhatsApp.
        
        Endpoint UAZAPI: POST /group/create
        Doc: https://docs.uazapi.com/

        Args:
            group_name: Nome do grupo
            description: Descrição do grupo (aplicada após criação)
            image_url: URL da imagem do grupo (aplicada após criação)

        Returns:
            Resposta completa da API com dados do grupo criado
        """
        logger.info(f"🔧 Criando grupo: {group_name}")

        endpoint = "/group/create"
        
        # Formato correto da UAZAPI
        payload = {
            "name": group_name,
            "participants": [self.admin_number]  # Lista de números para adicionar
        }

        logger.debug(f"Payload: {payload}")

        response = self._make_request("POST", endpoint, data=payload)

        if response:
            # Extrai o JID do grupo da resposta
            # A resposta pode vir como {"JID": "..."} ou {"group": {"JID": "..."}}
            group_data = response.get("group", response)
            group_jid = group_data.get("JID") or response.get("JID") or response.get("jid")
            
            if group_jid:
                # Adiciona o JID ao log para rastreamento
                if self.api_logs:
                    self.api_logs[-1].group_id_api = group_jid
                
                logger.info(f"✓ Grupo criado com sucesso: {group_name} (JID: {group_jid})")
                
                # Aguarda rate limit antes de configurar o grupo
                self.wait_rate_limit()
                
                # Atualiza descrição se fornecida
                if description:
                    logger.info(f"📝 Configurando descrição do grupo...")
                    success = self.update_group_description(group_jid, description)
                    if success:
                        logger.info(f"✓ Descrição configurada")
                    self.wait_rate_limit()
                
                # Atualiza imagem se fornecida
                if image_url:
                    logger.info(f"🖼️ Configurando imagem do grupo...")
                    success = self.update_group_picture(group_jid, image_url)
                    if success:
                        logger.info(f"✓ Imagem configurada")
                    self.wait_rate_limit()
                
                # Configura para somente admins poderem enviar mensagens
                logger.info(f"🔒 Configurando permissões (somente admins podem enviar msgs)...")
                success = self.set_group_messaging_permissions(group_jid, only_admins=True)
                if success:
                    logger.info(f"✓ Permissões de mensagens configuradas")
                self.wait_rate_limit()
                
                # Configura para somente admins poderem editar info do grupo
                logger.info(f"🔐 Configurando permissões (somente admins podem editar)...")
                success = self.set_group_edit_permissions(group_jid, only_admins=True)
                if success:
                    logger.info(f"✓ Permissões de edição configuradas")
                    
            return response

        logger.error(f"✗ Falha ao criar grupo: {group_name}")
        return None

    def get_group_info(self, group_id: str, get_invite_link: bool = True) -> Optional[GroupInfoResponse]:
        """
        Obtém informações detalhadas de um grupo específico.
        
        Endpoint UAZAPI: POST /group/info
        Doc: https://docs.uazapi.com/

        Args:
            group_id: JID do grupo (ex: 120363123456789@g.us)
            get_invite_link: Se deve buscar o link de convite

        Returns:
            Informações do grupo ou None
        """
        logger.debug(f"🔍 Buscando informações do grupo: {group_id}")

        endpoint = "/group/info"
        
        # Formato correto da UAZAPI
        payload = {
            "groupjid": group_id,
            "getInviteLink": get_invite_link  # true para buscar o link
        }

        response = self._make_request("POST", endpoint, data=payload)

        if response:
            # Adiciona o JID ao log
            if self.api_logs:
                self.api_logs[-1].group_id_api = group_id
                
            try:
                # Estrutura da resposta UAZAPI:
                # {
                #   "JID": "120363123456789@g.us",
                #   "Subject": "Nome do Grupo",
                #   "Participants": [...],
                #   "invite_link": "https://chat.whatsapp.com/...",
                #   ...
                # }
                
                group_jid = response.get("JID") or group_id
                subject = response.get("Subject", "")
                participants = response.get("Participants", [])
                member_count = len(participants) if isinstance(participants, list) else 0
                invite_link = response.get("invite_link", "")
                
                logger.debug(f"✓ Grupo encontrado: {subject} ({member_count} membros)")
                
                return GroupInfoResponse(
                    group_id=group_jid,
                    name=subject,
                    member_count=member_count,
                    invite_link=invite_link
                )

            except Exception as e:
                logger.error(f"✗ Erro ao parsear resposta do grupo: {e}")
                logger.error(f"Resposta recebida: {response}")
                return None

        return None

    def get_group_members_count(self, group_id: str) -> Optional[int]:
        """
        Obtém a contagem de membros de um grupo.

        Args:
            group_id: JID do grupo

        Returns:
            Número de membros ou None
        """
        info = self.get_group_info(group_id, get_invite_link=False)

        if info:
            logger.debug(f"✓ Grupo {group_id}: {info.member_count} membros")
            return info.member_count

        return None

    def get_group_invite_link(self, group_id: str) -> Optional[str]:
        """
        Obtém o link de convite de um grupo.

        Args:
            group_id: JID do grupo

        Returns:
            Link de convite ou None
        """
        logger.debug(f"🔗 Obtendo link de convite: {group_id}")

        # Usa get_group_info com getInviteLink=true
        info = self.get_group_info(group_id, get_invite_link=True)
        
        if info and info.invite_link:
            logger.info(f"✓ Link obtido: {info.invite_link}")
            return info.invite_link

        logger.error(f"✗ Falha ao obter link de convite: {group_id}")
        return None

    def revoke_group_invite_link(self, group_id: str) -> Optional[str]:
        """
        Revoga o link de convite atual e gera um novo.
        
        Endpoint UAZAPI: POST /group/invitecodereset
        
        Args:
            group_id: JID do grupo

        Returns:
            Novo link de convite ou None
        """
        logger.info(f"🔄 Revogando link de convite: {group_id}")

        endpoint = "/group/invitecodereset"
        payload = {"groupjid": group_id}
        
        response = self._make_request("POST", endpoint, data=payload)
        
        if response:
            # Adiciona o JID ao log
            if self.api_logs:
                self.api_logs[-1].group_id_api = group_id
                
            new_link = response.get("invite_link") or response.get("inviteLink")
            
            if new_link:
                logger.info(f"✓ Novo link gerado: {new_link}")
                return new_link

        logger.error(f"✗ Falha ao revogar link de convite: {group_id}")
        return None

    def add_participant_to_group(self, group_id: str, phone_number: str) -> bool:
        """
        Adiciona um participante a um grupo.
        
        Endpoint UAZAPI: POST /group/manageparticipants
        
        Args:
            group_id: JID do grupo
            phone_number: Número do telefone (formato: 5533987610311)

        Returns:
            True se adicionado com sucesso, False caso contrário
        """
        logger.info(f"➕ Adicionando {phone_number} ao grupo {group_id}")

        endpoint = "/group/manageparticipants"
        payload = {
            "groupjid": group_id,
            "action": "add",  # add, remove, promote, demote
            "participants": [phone_number]
        }

        response = self._make_request("POST", endpoint, data=payload)
        
        if response:
            # Adiciona o JID ao log
            if self.api_logs:
                self.api_logs[-1].group_id_api = group_id
                
            logger.info(f"✓ Participante {phone_number} adicionado ao grupo")
            return True

        logger.error(f"✗ Falha ao adicionar participante ao grupo")
        return False

    def list_groups(self, force: bool = False, no_participants: bool = True) -> Optional[List[Dict[str, Any]]]:
        """
        Lista todos os grupos.
        
        Endpoint UAZAPI: GET /group/list
        
        Args:
            force: Força atualização do cache
            no_participants: Não retorna a lista de participantes (mais rápido)

        Returns:
            Lista de grupos ou None
        """
        logger.debug("📋 Listando grupos...")

        endpoint = "/group/list"
        params = {}
        
        if force:
            params["force"] = "true"
        if no_participants:
            params["noparticipants"] = "true"
            
        response = self._make_request("GET", endpoint, params=params if params else None)

        if response:
            # A UAZAPI retorna um array direto de grupos
            if isinstance(response, list):
                logger.info(f"✓ {len(response)} grupos encontrados")
                return response
            
            # Ou pode vir em um wrapper
            if isinstance(response, dict) and "groups" in response:
                groups = response["groups"]
                logger.info(f"✓ {len(groups)} grupos encontrados")
                return groups

            logger.warning(f"Formato de resposta inesperado: {type(response)}")
            return None

        return None

    def wait_rate_limit(self):
        """
        Aguarda o delay configurado entre chamadas para evitar rate limit.
        """
        delay = settings.api_call_delay
        logger.debug(f"⏳ Aguardando {delay}s (rate limit protection)")
        time.sleep(delay)
    
    def update_group_description(self, group_id: str, description: str) -> bool:
        """
        Atualiza a descrição de um grupo.
        
        Endpoint UAZAPI: POST /group/updateDescription
        
        Args:
            group_id: JID do grupo
            description: Nova descrição do grupo

        Returns:
            True se atualizado com sucesso, False caso contrário
        """
        logger.debug(f"📝 Atualizando descrição do grupo {group_id}")

        endpoint = "/group/updateDescription"
        payload = {
            "groupjid": group_id,
            "description": description
        }

        response = self._make_request("POST", endpoint, data=payload)
        
        if response:
            if self.api_logs:
                self.api_logs[-1].group_id_api = group_id
                
            logger.info(f"✓ Descrição atualizada com sucesso")
            return True

        logger.error(f"✗ Falha ao atualizar descrição do grupo")
        return False
    
    def update_group_picture(self, group_id: str, image_url: str) -> bool:
        """
        Atualiza a imagem de um grupo.
        
        Endpoint UAZAPI: POST /group/updateImage
        
        Args:
            group_id: JID do grupo
            image_url: URL da imagem do grupo (deve ser JPEG, máx 640x640)

        Returns:
            True se atualizado com sucesso, False caso contrário
        """
        logger.debug(f"🖼️ Atualizando imagem do grupo {group_id}")

        endpoint = "/group/updateImage"
        payload = {
            "groupjid": group_id,
            "image": image_url
        }

        response = self._make_request("POST", endpoint, data=payload)
        
        if response:
            if self.api_logs:
                self.api_logs[-1].group_id_api = group_id
                
            logger.info(f"✓ Imagem atualizada com sucesso")
            return True

        logger.error(f"✗ Falha ao atualizar imagem do grupo")
        return False
    
    def set_group_messaging_permissions(self, group_id: str, only_admins: bool = True) -> bool:
        """
        Configura as permissões de envio de mensagens no grupo.
        
        Endpoint UAZAPI: POST /group/updateAnnounce
        
        Quando ativado (announce=True):
        - Apenas administradores podem enviar mensagens
        - Outros participantes podem apenas ler
        - Útil para anúncios importantes ou controle de spam
        
        Quando desativado (announce=False):
        - Todos os participantes podem enviar mensagens
        
        Args:
            group_id: JID do grupo
            only_admins: True para apenas admins, False para todos

        Returns:
            True se configurado com sucesso, False caso contrário
        """
        logger.debug(f"🔒 Configurando permissões de msg do grupo {group_id} (somente admins: {only_admins})")

        endpoint = "/group/updateAnnounce"
        payload = {
            "groupjid": group_id,
            "announce": only_admins
        }

        response = self._make_request("POST", endpoint, data=payload)
        
        if response:
            if self.api_logs:
                self.api_logs[-1].group_id_api = group_id
                
            permission_text = "Somente administradores" if only_admins else "Todos os participantes"
            logger.info(f"✓ Permissões configuradas: {permission_text}")
            return True

        logger.error(f"✗ Falha ao configurar permissões do grupo")
        return False
    
    def set_group_edit_permissions(self, group_id: str, only_admins: bool = True) -> bool:
        """
        Configura as permissões de edição das informações do grupo.
        
        Endpoint UAZAPI: POST /group/updateLocked
        
        Quando bloqueado (locked=True):
        - Apenas administradores podem editar nome, descrição, imagem e outras configurações
        - Outros participantes não podem modificar informações do grupo
        
        Quando desbloqueado (locked=False):
        - Qualquer participante pode editar as informações do grupo
        
        Args:
            group_id: JID do grupo
            only_admins: True para apenas admins editarem, False para todos

        Returns:
            True se configurado com sucesso, False caso contrário
        """
        logger.debug(f"🔐 Configurando permissões de edição do grupo {group_id} (somente admins: {only_admins})")

        endpoint = "/group/updateLocked"
        payload = {
            "groupjid": group_id,
            "locked": only_admins
        }

        response = self._make_request("POST", endpoint, data=payload)
        
        if response:
            if self.api_logs:
                self.api_logs[-1].group_id_api = group_id
                
            permission_text = "Somente administradores" if only_admins else "Todos os participantes"
            logger.debug(f"✓ Permissões de edição configuradas: {permission_text}")
            return True

        logger.error(f"✗ Falha ao configurar permissões de edição do grupo")
        return False

    def get_api_logs(self) -> List[ApiCallLog]:
        """
        Retorna os logs de chamadas à API.

        Returns:
            Lista de logs
        """
        return self.api_logs

    def clear_api_logs(self):
        """
        Limpa os logs de chamadas à API (após salvar no banco).
        """
        self.api_logs = []
