"""
Modelos de dados do sistema.
"""
from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel


class WhatsAppGroup(BaseModel):
    """Modelo de um grupo de WhatsApp"""

    id: Optional[str] = None
    group_id_api: str  # Campo JID da API (ex: 120363123456789@g.us)
    name: str
    invite_link: str
    member_count: int
    is_active: bool = True
    
    # Campos adicionais da API UAZAPI
    subject: Optional[str] = None  # Nome/assunto do grupo
    description: Optional[str] = None  # Descrição do grupo (Desc)
    owner_jid: Optional[str] = None  # JID do dono (OwnerJID)
    created_timestamp: Optional[int] = None  # Timestamp de criação (Creation)
    participant_version_id: Optional[str] = None  # ParticipantVersionID
    is_announcement: Optional[bool] = None  # GroupIsAnnounce
    is_locked: Optional[bool] = None  # GroupIsLocked
    is_parent: Optional[bool] = None  # IsParent
    default_membership_approval_mode: Optional[bool] = None  # DefaultMembershipApprovalMode
    is_incognito: Optional[bool] = None  # IsIncognito
    linked_parent_jid: Optional[str] = None  # LinkedParentJID para grupos de comunidade
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class GroupCreateRequest(BaseModel):
    """Request para criar um novo grupo"""
    name: str
    description: Optional[str] = None


class GroupInfoResponse(BaseModel):
    """Resposta com informações do grupo da API"""
    group_id: str
    name: str
    member_count: int
    invite_link: Optional[str] = None


class LoadBalancerResult(BaseModel):
    """Resultado do algoritmo de load balancer"""
    group: Optional[WhatsAppGroup] = None
    should_create_new: bool = False
    reason: str


class MonitorLog(BaseModel):
    """Modelo de log de monitoramento"""

    id: Optional[str] = None
    monitor_type: str  # 'newest_group' ou 'full_sync'
    group_id_api: Optional[str] = None
    group_name: Optional[str] = None
    member_count: Optional[int] = None
    previous_count: Optional[int] = None
    count_difference: Optional[int] = None
    new_group_created: bool = False
    new_group_id_api: Optional[str] = None
    status_message: Optional[str] = None
    has_error: bool = False
    error_message: Optional[str] = None
    checked_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ApiCallLog(BaseModel):
    """Modelo de log de chamadas à API do WhatsApp"""
    
    id: Optional[str] = None
    endpoint: str  # Endpoint chamado (ex: /group/create, /group/info)
    method: str  # Método HTTP (GET, POST)
    request_payload: Optional[Dict[str, Any]] = None  # Dados enviados
    response_data: Optional[Dict[str, Any]] = None  # Resposta da API
    status_code: Optional[int] = None  # Status HTTP (200, 400, 500)
    success: bool = False  # Se a chamada foi bem sucedida
    error_message: Optional[str] = None  # Mensagem de erro, se houver
    duration_ms: Optional[int] = None  # Duração da chamada em milissegundos
    group_id_api: Optional[str] = None  # ID do grupo relacionado
    called_at: Optional[datetime] = None  # Timestamp da chamada
    
    class Config:
        from_attributes = True
