"""
Rastreio nominal de membros e atribuição de anúncio.

O painel sempre soube QUANTOS entraram e saíram — painel_fluxo_diario deriva
isso da diferença de member_count. O que faltava era QUEM e DE ONDE: sem isso
não dá para ver que as 3 pessoas que saíram hoje vieram todas do mesmo anúncio,
que é o sinal de que aquele criativo promete o que o grupo não entrega.

Como funciona
-------------
`POST /group/info` já devolve o array `Participants` a cada ciclo do monitor —
o código só usava o `len()` dele. Comparar esse array com o roster salvo
(`grupo_membros`) dá entrada e saída nominais, sem webhook novo e sem uma única
chamada de API a mais.

O elo com o anúncio é o ponto delicado: o link de convite do WhatsApp não
carrega parâmetro, então não existe nada dentro da entrada que diga de onde a
pessoa veio. A ligação é feita por PAREAMENTO POR TEMPO — a landing grava cada
clique no CTA em `cliques_anuncio` (com as UTMs e o grupo de destino), e cada
entrada nova consome o clique mais recente ainda não usado daquele grupo.

Isso é uma inferência, não um fato, e o código diz isso em voz alta:

    direta       1 candidato, ou vários candidatos do MESMO anúncio
    ambigua      vários candidatos de anúncios diferentes — pegamos o mais
                 recente, mas pode ser o outro
    organica     nenhum clique na janela: veio de indicação, link repassado,
                 ou de um clique mais velho que a janela
    preexistente já estava no grupo quando o rastreio começou

Com o volume atual (unidades de entrada por dia) a ambiguidade é rara. Se ela
crescer, o caminho é identificar a pessoa antes da entrada (código por DM) —
`clique_id` continua sendo a chave, só muda como se descobre qual é.

Chave de acesso
---------------
`grupo_membros` e `grupo_eventos` guardam telefone de gente real, e a chave
anon do projeto está publicada no JS da landing page. Por isso as duas tabelas
têm RLS ligada sem nenhuma policy de leitura, e este módulo é o único lugar do
sistema que usa a SUPABASE_SERVICE_KEY. Sem essa variável o rastreio fica
desligado — nunca cai para a chave anon, que só funcionaria se as tabelas
fossem legíveis por qualquer visitante da landing.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from supabase import create_client, Client

from .config import settings
from .models import EventoGrupo, MembroGrupo, WhatsAppGroup

logger = logging.getLogger(__name__)

# Identidade de um participante: (jid, lid). Pelo menos um dos dois é não-nulo.
Identidade = Tuple[Optional[str], Optional[str]]


# =============================================================================
# Funções puras — sem rede, sem banco. É aqui que mora a decisão, e é isto que
# test_atribuicao.py cobre.
# =============================================================================

def identidade(participante: dict) -> Identidade:
    """
    Extrai (jid, lid) de um item do array Participants da UAZAPI.

    O WhatsApp está migrando de JID de telefone (`...@s.whatsapp.net`) para LID
    (`...@lid`), e a API pode devolver um, outro ou os dois. Guardamos ambos
    para reconhecer a mesma pessoa se a resposta alternar entre eles — senão ela
    apareceria como uma saída seguida de uma entrada, churn que nunca houve.
    """
    if not isinstance(participante, dict):
        return (None, None)

    def _limpa(valor) -> Optional[str]:
        if not isinstance(valor, str):
            return None
        valor = valor.strip().lower()
        return valor or None

    jid = _limpa(participante.get("JID") or participante.get("jid"))
    lid = _limpa(participante.get("LID") or participante.get("lid"))

    # Alguns retornos trazem o LID no campo JID. Normaliza para que o LID
    # sempre caia na coluna de LID.
    if jid and jid.endswith("@lid") and not lid:
        jid, lid = None, jid

    return (jid, lid)


def chave(ident: Identidade) -> Optional[str]:
    """
    A coluna `participante_jid` (parte da PK de grupo_membros).

    Prefere o JID de telefone; cai para o LID quando é só o que existe.
    """
    jid, lid = ident
    return jid or lid


def _chave_anuncio(clique: dict) -> str:
    """Identidade do anúncio dentro de um clique, para comparar candidatos."""
    return (clique.get("utm_content") or clique.get("anuncio_id")
            or clique.get("utm_campaign") or "")


def _campanha(clique: dict) -> Optional[str]:
    return clique.get("utm_campaign") or clique.get("utm_id")


def _anuncio(clique: dict) -> Optional[str]:
    return clique.get("utm_content") or clique.get("anuncio_id")


def diff_roster(
    participantes: List[dict],
    salvos: List[MembroGrupo],
) -> Tuple[List[Identidade], List[MembroGrupo]]:
    """
    Compara o roster da API com o do banco.

    Devolve (novos, saíram). O casamento aceita JID OU LID: basta um dos dois
    bater para a pessoa ser considerada a mesma (ver `identidade`).
    """
    jids_salvos = {m.participante_jid for m in salvos if m.participante_jid}
    lids_salvos = {m.participante_lid for m in salvos if m.participante_lid}

    novos: List[Identidade] = []
    vistos_agora_jid: set = set()
    vistos_agora_lid: set = set()

    for participante in participantes:
        ident = identidade(participante)
        jid, lid = ident
        if not chave(ident):
            continue  # item sem identificação nenhuma: não dá para rastrear

        if jid:
            vistos_agora_jid.add(jid)
        if lid:
            vistos_agora_lid.add(lid)

        conhecido = (jid in jids_salvos) or (lid is not None and lid in lids_salvos)
        if not conhecido:
            novos.append(ident)

    sairam = [
        m for m in salvos
        if m.participante_jid not in vistos_agora_jid
        and (m.participante_lid is None or m.participante_lid not in vistos_agora_lid)
    ]

    return novos, sairam


def atribuir_entradas(
    novos: List[Identidade],
    cliques: List[dict],
) -> List[Tuple[Identidade, Optional[dict], str]]:
    """
    Casa cada entrada nova com um clique da landing.

    Args:
        novos: identidades que apareceram no grupo neste ciclo.
        cliques: candidatos daquele grupo, ainda não consumidos, do MAIS
            RECENTE para o mais antigo, já filtrados pela janela de tempo.

    Returns:
        Uma tupla (identidade, clique ou None, atribuição) por entrada. O
        pareamento é 1:1 — dois que entram no mesmo ciclo nunca dividem o mesmo
        clique, senão um anúncio levaria crédito em dobro.
    """
    fila = list(cliques)
    resultado: List[Tuple[Identidade, Optional[dict], str]] = []

    for ident in novos:
        if not fila:
            resultado.append((ident, None, "organica"))
            continue

        # Vários candidatos do mesmo anúncio dão a mesma resposta por qualquer
        # caminho — só chamamos de ambígua quando a escolha muda o resultado.
        um_so_anuncio = len({_chave_anuncio(c) for c in fila}) == 1
        atribuicao = "direta" if (len(fila) == 1 or um_so_anuncio) else "ambigua"

        resultado.append((ident, fila.pop(0), atribuicao))

    return resultado


def permanencia_em_minutos(entrou_em: Optional[datetime], agora: datetime) -> Optional[int]:
    """Minutos entre a entrada e a saída. None quando a entrada é desconhecida."""
    if not entrou_em:
        return None
    if entrou_em.tzinfo is None:
        entrou_em = entrou_em.replace(tzinfo=timezone.utc)
    return max(0, int((agora - entrou_em).total_seconds() // 60))


# =============================================================================
# Repositório — o lado com banco
# =============================================================================

class RepositorioMembros:
    """
    Acesso às tabelas do rastreio, com a service key.

    `disponivel` False significa que SUPABASE_SERVICE_KEY não foi configurada:
    o rastreio simplesmente não roda, e nada mais no monitor muda.
    """

    def __init__(self):
        self.client: Optional[Client] = None

        if settings.supabase_service_key:
            self.client = create_client(
                settings.supabase_url,
                settings.supabase_service_key,
            )
        else:
            logger.warning(
                "⚠ SUPABASE_SERVICE_KEY ausente — rastreio de membros por anúncio "
                "DESLIGADO. O painel continua mostrando o fluxo por contagem."
            )

    @property
    def disponivel(self) -> bool:
        return self.client is not None

    # ---------------------------------------------------------------- roster
    # O PostgREST corta a resposta no `max-rows` do projeto (1000 por padrão no
    # Supabase), e um grupo do WhatsApp vai até 1024 membros. Sem paginar, os
    # membros além do corte sumiriam da lista e o diff os leria como uma saída em
    # massa — inventando churn que nunca houve.
    PAGINA = 1000

    def carregar_roster(self, grupo_id: str) -> List[MembroGrupo]:
        """Roster salvo de um grupo. Levanta em falha de consulta: tratar erro
        como 'grupo vazio' faria o próximo ciclo registrar o grupo inteiro
        entrando de novo."""
        linhas: List[dict] = []
        inicio = 0

        while True:
            resposta = (
                self.client.table("grupo_membros")
                .select("*")
                .eq("grupo_id", grupo_id)
                .order("participante_jid")
                .range(inicio, inicio + self.PAGINA - 1)
                .execute()
            )
            pagina = resposta.data or []
            linhas.extend(pagina)
            if len(pagina) < self.PAGINA:
                break
            inicio += self.PAGINA

        return [MembroGrupo(**linha) for linha in linhas]

    def semear_roster(self, grupo_id: str, participantes: List[dict]) -> int:
        """
        Primeira leitura de um grupo: grava todo mundo como 'preexistente' e NÃO
        emite evento nenhum.

        Sem isso, o primeiro ciclo registraria os 800 membros atuais como
        entradas de hoje e arruinaria qualquer média do painel.
        """
        linhas = []
        for participante in participantes:
            ident = identidade(participante)
            if not chave(ident):
                continue
            linhas.append({
                "grupo_id": grupo_id,
                "participante_jid": chave(ident),
                "participante_lid": ident[1],
                "atribuicao": "preexistente",
            })

        if not linhas:
            return 0

        self.client.table("grupo_membros").upsert(
            linhas, on_conflict="grupo_id,participante_jid"
        ).execute()
        return len(linhas)

    # --------------------------------------------------------------- cliques
    def buscar_cliques(self, group_jid: str, desde: datetime) -> List[dict]:
        """Cliques candidatos daquele grupo: não consumidos, dentro da janela,
        do mais recente para o mais antigo."""
        resposta = (
            self.client.table("cliques_anuncio")
            .select("*")
            .eq("group_jid", group_jid)
            .is_("consumido_em", "null")
            .gte("criado_em", desde.isoformat())
            .order("criado_em", desc=True)
            .execute()
        )
        return resposta.data or []

    def consumir_clique(self, clique_id: str, agora: datetime) -> None:
        self.client.table("cliques_anuncio").update(
            {"consumido_em": agora.isoformat()}
        ).eq("id", clique_id).execute()

    # --------------------------------------------------------------- eventos
    def registrar_entradas(self, membros: List[MembroGrupo], eventos: List[EventoGrupo]) -> None:
        if membros:
            self.client.table("grupo_membros").upsert(
                [m.model_dump(mode="json", exclude_none=True) for m in membros],
                on_conflict="grupo_id,participante_jid",
            ).execute()
        self._salvar_eventos(eventos)

    def registrar_saidas(self, grupo_id: str, jids: List[str], eventos: List[EventoGrupo]) -> None:
        # O evento é gravado ANTES de apagar a linha do roster: se a remoção
        # falhar, sobra uma linha a mais (corrigida no próximo ciclo); na ordem
        # inversa, perder-se-ia a origem da saída para sempre.
        self._salvar_eventos(eventos)
        if jids:
            self.client.table("grupo_membros").delete().eq(
                "grupo_id", grupo_id
            ).in_("participante_jid", jids).execute()

    def _salvar_eventos(self, eventos: List[EventoGrupo]) -> None:
        if not eventos:
            return
        self.client.table("grupo_eventos").insert(
            [e.model_dump(mode="json", exclude_none=True) for e in eventos]
        ).execute()


# =============================================================================
# Orquestração
# =============================================================================

class RastreadorMembros:
    """Junta o diff do roster, o pareamento e a escrita no banco."""

    def __init__(self, repositorio: Optional[RepositorioMembros] = None):
        self.repo = repositorio or RepositorioMembros()

    @property
    def disponivel(self) -> bool:
        return self.repo.disponivel

    def sincronizar(self, grupo: WhatsAppGroup, participantes: List[dict]) -> Dict[str, int]:
        """
        Confere o roster de um grupo contra o que a API acabou de devolver.

        Args:
            grupo: o grupo, já com `id` (PK) e `nicho_id` vindos do banco.
            participantes: array Participants da mesma chamada /group/info que
                atualizou a contagem de membros — nunca uma chamada nova.

        Returns:
            {"entradas": n, "saidas": n, "semeados": n}. Falha de banco é logada
            e devolvida zerada: rastreio é observabilidade, e nunca pode
            derrubar o balanceador, que é o que mantém os grupos no ar.
        """
        vazio = {"entradas": 0, "saidas": 0, "semeados": 0}

        if not self.disponivel or not grupo.id:
            return vazio

        agora = datetime.now(timezone.utc)

        try:
            salvos = self.repo.carregar_roster(grupo.id)

            # Cold start: grupo ainda sem roster no banco.
            if not salvos:
                semeados = self.repo.semear_roster(grupo.id, participantes)
                logger.info(
                    f"🌱 Roster inicial de {grupo.name}: {semeados} membro(s) "
                    f"marcados como preexistentes (sem evento de entrada)"
                )
                return {**vazio, "semeados": semeados}

            novos, sairam = diff_roster(participantes, salvos)

            # O caso comum é nada ter mudado. Carimbar "conferido agora" em cada
            # membro custaria centenas de UPDATEs por minuto para registrar que
            # não aconteceu nada; quem prova que o rastreio está vivo é
            # painel_saude_monitor.
            if not novos and not sairam:
                return vazio

            entradas = self._processar_entradas(grupo, novos, agora)
            saidas = self._processar_saidas(grupo, sairam, agora)

            logger.info(
                f"👥 {grupo.name}: {entradas} entrada(s), {saidas} saída(s) "
                f"registradas com origem"
            )
            return {"entradas": entradas, "saidas": saidas, "semeados": 0}

        except Exception as e:
            logger.error(f"✗ Falha no rastreio de membros de {grupo.name}: {e}", exc_info=True)
            return vazio

    def _processar_entradas(
        self, grupo: WhatsAppGroup, novos: List[Identidade], agora: datetime
    ) -> int:
        if not novos:
            return 0

        desde = agora - timedelta(minutes=settings.atribuicao_janela_min)
        cliques = self.repo.buscar_cliques(grupo.group_id_api, desde)

        membros: List[MembroGrupo] = []
        eventos: List[EventoGrupo] = []

        for ident, clique, atribuicao in atribuir_entradas(novos, cliques):
            campanha = _campanha(clique) if clique else None
            anuncio = _anuncio(clique) if clique else None
            clique_id = clique.get("id") if clique else None

            membros.append(MembroGrupo(
                grupo_id=grupo.id,
                participante_jid=chave(ident),
                participante_lid=ident[1],
                entrou_em=agora,
                visto_em=agora,
                clique_id=clique_id,
                atribuicao=atribuicao,
                campanha=campanha,
                anuncio=anuncio,
            ))
            eventos.append(EventoGrupo(
                grupo_id=grupo.id,
                nicho_id=grupo.nicho_id,
                participante_jid=chave(ident),
                tipo="entrada",
                ocorrido_em=agora,
                clique_id=clique_id,
                atribuicao=atribuicao,
                campanha=campanha,
                anuncio=anuncio,
            ))

            if clique_id:
                self.repo.consumir_clique(clique_id, agora)

        self.repo.registrar_entradas(membros, eventos)
        return len(membros)

    def _processar_saidas(
        self, grupo: WhatsAppGroup, sairam: List[MembroGrupo], agora: datetime
    ) -> int:
        if not sairam:
            return 0

        eventos = [
            EventoGrupo(
                grupo_id=grupo.id,
                nicho_id=grupo.nicho_id,
                participante_jid=membro.participante_jid,
                tipo="saida",
                ocorrido_em=agora,
                # Tudo herdado do roster: é o que faz a saída dizer de qual
                # anúncio a pessoa tinha vindo.
                clique_id=membro.clique_id,
                atribuicao=membro.atribuicao,
                campanha=membro.campanha,
                anuncio=membro.anuncio,
                permanencia_min=permanencia_em_minutos(membro.entrou_em, agora),
            )
            for membro in sairam
        ]

        self.repo.registrar_saidas(
            grupo.id, [m.participante_jid for m in sairam], eventos
        )
        return len(eventos)
