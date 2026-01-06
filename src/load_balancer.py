"""
Algoritmo de Load Balancer e Auto-Scaling para grupos de WhatsApp.
"""
import logging
from typing import Optional

from .config import settings
from .supabase_client import SupabaseClient
from .whatsapp_service import WhatsAppService
from .models import WhatsAppGroup, LoadBalancerResult

logger = logging.getLogger(__name__)


class LoadBalancer:
    """
    Gerencia a distribuição inteligente de leads entre grupos de WhatsApp.
    """

    def __init__(self):
        self.db = SupabaseClient()
        self.whatsapp = WhatsAppService()
        self.max_redirect = settings.max_members_for_redirect
        self.scale_threshold = settings.scale_out_threshold

    def get_best_group_for_lead(self) -> LoadBalancerResult:
        """
        Algoritmo principal: Retorna o melhor grupo para receber um novo lead.

        Regras:
        1. Busca o grupo com MENOR número de membros
        2. Esse grupo deve ter MENOS de 900 membros (max_redirect)
        3. Se não houver grupo disponível, sinaliza necessidade de criar novo

        Returns:
            LoadBalancerResult com o grupo ideal ou indicação de criar novo
        """
        logger.info("🎯 Buscando melhor grupo para novo lead...")

        # Busca o grupo com menor member_count que esteja abaixo do limite
        best_group = self.db.get_best_group_for_redirect(self.max_redirect)

        if best_group:
            logger.info(
                f"✓ Grupo selecionado: {best_group.name} "
                f"({best_group.member_count}/{self.max_redirect} membros)"
            )
            return LoadBalancerResult(
                group=best_group,
                should_create_new=False,
                reason=f"Grupo disponível com {best_group.member_count} membros"
            )

        # Nenhum grupo disponível
        logger.warning(
            f"⚠ ALERTA: Nenhum grupo com menos de {self.max_redirect} membros! "
            "Criação de novo grupo necessária."
        )

        return LoadBalancerResult(
            group=None,
            should_create_new=True,
            reason=f"Todos os grupos estão com {self.max_redirect}+ membros"
        )

    def should_scale_out(self, group: WhatsAppGroup) -> bool:
        """
        Verifica se um grupo atingiu o threshold para criar um novo.

        Args:
            group: Grupo a ser verificado

        Returns:
            True se deve criar novo grupo, False caso contrário
        """
        if group.member_count >= self.scale_threshold:
            logger.warning(
                f"🚨 SCALE-OUT TRIGGER: {group.name} atingiu {group.member_count} membros "
                f"(threshold: {self.scale_threshold})"
            )
            return True

        return False

    def create_new_group(self, group_number: Optional[int] = None, group_name: Optional[str] = None) -> Optional[WhatsAppGroup]:
        """
        Cria um novo grupo via API e registra no banco de dados.

        Args:
            group_number: Número do grupo (ex: 101). Se None, calcula automaticamente.
            group_name: Nome do grupo customizado. Se None, usa padrão "Grupo {number}"

        Returns:
            Grupo criado ou None em caso de erro
        """
        # Determina o número do próximo grupo se não fornecido
        if group_number is None:
            active_groups = self.db.get_active_groups()
            group_number = len(active_groups) + 1

        # Usa nome customizado ou padrão
        if not group_name:
            group_name = f"Grupo {group_number}"

        logger.info(f"🔧 Criando novo grupo: {group_name}")

        # Cria o grupo via API do WhatsApp com descrição e imagem das envs
        api_response = self.whatsapp.create_group(
            group_name, 
            settings.group_description,
            settings.group_image_url
        )

        if not api_response:
            logger.error(f"✗ Falha ao criar grupo via API: {group_name}")
            # Salva logs da API no banco
            self._save_api_logs()
            return None

        # Extrai informações da resposta UAZAPI
        # Estrutura esperada: {"group": {"JID": "120363123456789@g.us", "Name": "..."}}
        group_data = api_response.get("group", {})
        group_id_api = group_data.get("JID") or api_response.get("JID")
        subject = group_data.get("Name", group_name)
        
        if not group_id_api:
            logger.error(f"✗ API não retornou JID do grupo. Resposta: {api_response}")
            self._save_api_logs()
            return None

        # Aguarda rate limit
        self.whatsapp.wait_rate_limit()

        # Obtém o link de convite
        invite_link = self.whatsapp.get_group_invite_link(group_id_api)
        if not invite_link:
            logger.warning("⚠ Link de convite não obtido, usando vazio")
            invite_link = ""

        # Salva informações extras da API se disponíveis
        owner_jid = group_data.get("OwnerJID")
        created_timestamp = group_data.get("GroupCreated")
        is_announcement = group_data.get("IsAnnounce", False)
        is_locked = group_data.get("IsLocked", False)
        topic = group_data.get("Topic", "")
        participants = group_data.get("Participants", [])
        member_count = len(participants) if participants else 1

        # Cria objeto do grupo
        new_group = WhatsAppGroup(
            group_id_api=group_id_api,
            name=subject,
            invite_link=invite_link or "",
            member_count=member_count,
            is_active=True,
            subject=subject,
            description=topic,
            owner_jid=owner_jid,
            created_timestamp=None,  # Converter depois se necessário
            is_announcement=is_announcement,
            is_locked=is_locked
        )

        # Salva no banco de dados
        created_group = self.db.create_group(new_group)

        # Salva logs da API
        self._save_api_logs()

        if created_group:
            logger.info(
                f"✅ NOVO GRUPO CRIADO COM SUCESSO!\n"
                f"   Nome: {created_group.name}\n"
                f"   ID API: {created_group.group_id_api}\n"
                f"   Link: {created_group.invite_link}"
            )
            return created_group

        logger.error("✗ Falha ao salvar grupo no banco de dados")
        return None

    def sync_group_members(self, group: WhatsAppGroup) -> bool:
        """
        Sincroniza a contagem de membros de um grupo com a API.

        Args:
            group: Grupo a ser sincronizado

        Returns:
            True se sincronizado com sucesso, False caso contrário
        """
        logger.debug(f"🔄 Sincronizando membros do grupo: {group.name}")

        # Busca contagem atualizada da API
        current_count = self.whatsapp.get_group_members_count(group.group_id_api)

        if current_count is None:
            logger.error(f"✗ Falha ao obter contagem de membros: {group.name}")
            return False

        # Se a contagem mudou, atualiza no banco
        if current_count != group.member_count:
            logger.info(
                f"📊 Atualização: {group.name} - "
                f"{group.member_count} → {current_count} membros"
            )

            success = self.db.update_member_count(group.group_id_api, current_count)

            if success:
                # Verifica se precisa escalar
                if current_count >= self.scale_threshold:
                    logger.warning(
                        f"🚨 ATENÇÃO: {group.name} atingiu {current_count} membros! "
                        f"Considere criar novo grupo."
                    )

            return success

        logger.debug(f"✓ {group.name} - Contagem inalterada ({current_count} membros)")
        return True

    def sync_all_groups(self) -> dict:
        """
        Sincroniza todos os grupos ativos com a API (Daily Sync).

        Returns:
            Estatísticas da sincronização
        """
        logger.info("🔄 INICIANDO SINCRONIZAÇÃO DIÁRIA DE TODOS OS GRUPOS")

        active_groups = self.db.get_active_groups()
        stats = {
            "total": len(active_groups),
            "success": 0,
            "failed": 0,
            "unchanged": 0
        }

        for index, group in enumerate(active_groups, 1):
            logger.info(f"📍 [{index}/{stats['total']}] Sincronizando: {group.name}")

            old_count = group.member_count
            success = self.sync_group_members(group)

            if success:
                # Verifica se houve mudança
                updated_group = self.db.get_group_by_api_id(group.group_id_api)
                if updated_group and updated_group.member_count != old_count:
                    stats["success"] += 1
                else:
                    stats["unchanged"] += 1
            else:
                stats["failed"] += 1

            # Delay entre chamadas para evitar rate limit
            if index < stats["total"]:
                self.whatsapp.wait_rate_limit()

        logger.info(
            f"✅ SINCRONIZAÇÃO CONCLUÍDA\n"
            f"   Total de grupos: {stats['total']}\n"
            f"   Atualizados: {stats['success']}\n"
            f"   Sem alteração: {stats['unchanged']}\n"
            f"   Falhas: {stats['failed']}"
        )

        return stats

    def _save_api_logs(self):
        """Salva os logs de API acumulados no banco de dados."""
        if not self.whatsapp.api_logs:
            return
        
        try:
            saved = self.db.save_api_call_logs_bulk(self.whatsapp.api_logs)
            if saved > 0:
                logger.debug(f"✓ {saved} logs de API salvos no banco")
            # Limpa o cache de logs
            self.whatsapp.api_logs.clear()
        except Exception as e:
            # Ignora erros de salvamento de logs (tabela pode não existir ainda)
            logger.debug(f"Logs de API não foram salvos: {e}")
            self.whatsapp.api_logs.clear()


        # Salva logs de API acumulados
        self._save_api_logs()

        return stats

    def _save_api_logs(self):
        """
        Salva todos os logs de chamadas API acumulados no banco de dados.
        """
        if not self.whatsapp.api_logs:
            return
            
        saved_count = self.db.save_api_call_logs_bulk(self.whatsapp.api_logs)
        
        if saved_count > 0:
            logger.debug(f"✓ {saved_count} logs de API salvos no banco")
        
        # Limpa a lista de logs
        self.whatsapp.api_logs.clear()
