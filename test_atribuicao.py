"""
Testes do rastreio de membros e da atribuição de anúncio (src/membros.py).

Só funções puras: diff de roster, pareamento clique→entrada e permanência.
Nada aqui toca o Supabase nem a UAZAPI — a parte de I/O é fina de propósito,
e a decisão toda (quem entrou, de qual anúncio veio, quanto tempo ficou) mora
nas funções testadas aqui.
"""
from datetime import datetime, timedelta, timezone

from src.membros import (
    RastreadorMembros,
    atribuir_entradas,
    chave,
    diff_roster,
    identidade,
    permanencia_em_minutos,
)
from src.models import MembroGrupo, WhatsAppGroup

GRUPO = "11111111-1111-1111-1111-111111111111"


def participante(jid=None, lid=None):
    p = {}
    if jid:
        p["JID"] = jid
    if lid:
        p["LID"] = lid
    return p


def membro(jid, lid=None, **kwargs):
    return MembroGrupo(grupo_id=GRUPO, participante_jid=jid, participante_lid=lid, **kwargs)


def clique(anuncio, campanha="campanha_x", id_="c1"):
    return {"id": id_, "utm_content": anuncio, "utm_campaign": campanha}


# ---------------------------------------------------------------- identidade

def test_identidade_prefere_jid_de_telefone():
    assert identidade(participante("5511999@s.whatsapp.net", "888@lid")) == (
        "5511999@s.whatsapp.net", "888@lid"
    )


def test_identidade_com_lid_no_campo_jid_vai_para_a_coluna_de_lid():
    # A API às vezes devolve o LID no campo JID. Deixar assim faria a mesma
    # pessoa ocupar duas linhas do roster.
    assert identidade(participante("888@lid")) == (None, "888@lid")


def test_chave_cai_para_o_lid_quando_nao_ha_telefone():
    assert chave(identidade(participante(lid="888@lid"))) == "888@lid"


# --------------------------------------------------------------- diff_roster

def test_diff_detecta_entrada_e_saida():
    salvos = [membro("a@s.whatsapp.net"), membro("b@s.whatsapp.net")]
    atuais = [participante("a@s.whatsapp.net"), participante("c@s.whatsapp.net")]

    novos, sairam = diff_roster(atuais, salvos)

    assert [chave(n) for n in novos] == ["c@s.whatsapp.net"]
    assert [m.participante_jid for m in sairam] == ["b@s.whatsapp.net"]


def test_diff_reconhece_a_mesma_pessoa_pelo_lid():
    # Se a API troca o JID de telefone pelo LID, a pessoa não pode virar uma
    # saída seguida de uma entrada: esse churn nunca aconteceu.
    salvos = [membro("a@s.whatsapp.net", lid="777@lid")]
    atuais = [participante(lid="777@lid")]

    novos, sairam = diff_roster(atuais, salvos)

    assert novos == []
    assert sairam == []


def test_diff_ignora_participante_sem_identificacao():
    novos, sairam = diff_roster([{"IsAdmin": True}], [])
    assert novos == []
    assert sairam == []


# --------------------------------------------------------- atribuir_entradas

def test_sem_clique_a_entrada_e_organica():
    resultado = atribuir_entradas([("a@s.whatsapp.net", None)], [])
    _, escolhido, atribuicao = resultado[0]
    assert escolhido is None
    assert atribuicao == "organica"


def test_um_clique_uma_entrada_e_atribuicao_direta():
    c = clique("criativo_A")
    resultado = atribuir_entradas([("a@s.whatsapp.net", None)], [c])
    _, escolhido, atribuicao = resultado[0]
    assert escolhido is c
    assert atribuicao == "direta"


def test_varios_cliques_do_mesmo_anuncio_ainda_sao_diretos():
    # A escolha não muda a resposta, então não há ambiguidade a declarar.
    cliques = [clique("criativo_A", id_="c1"), clique("criativo_A", id_="c2")]
    resultado = atribuir_entradas([("a@s.whatsapp.net", None)], cliques)
    assert resultado[0][2] == "direta"


def test_cliques_de_anuncios_diferentes_marcam_ambigua():
    cliques = [clique("criativo_B", id_="c1"), clique("criativo_A", id_="c2")]
    resultado = atribuir_entradas([("a@s.whatsapp.net", None)], cliques)
    _, escolhido, atribuicao = resultado[0]
    assert escolhido["id"] == "c1"  # o mais recente
    assert atribuicao == "ambigua"


def test_duas_entradas_nunca_dividem_o_mesmo_clique():
    # Senão um único clique creditaria duas entradas ao mesmo anúncio.
    cliques = [clique("criativo_A", id_="c1"), clique("criativo_A", id_="c2")]
    resultado = atribuir_entradas(
        [("a@s.whatsapp.net", None), ("b@s.whatsapp.net", None)], cliques
    )
    assert [r[1]["id"] for r in resultado] == ["c1", "c2"]


def test_entradas_alem_dos_cliques_sobram_como_organicas():
    resultado = atribuir_entradas(
        [("a@s.whatsapp.net", None), ("b@s.whatsapp.net", None)],
        [clique("criativo_A", id_="c1")],
    )
    assert [r[2] for r in resultado] == ["direta", "organica"]


def test_ultimo_clique_da_fila_deixa_de_ser_ambiguo():
    # Com dois anúncios na disputa a primeira entrada é ambígua; consumido um
    # deles, sobra um só candidato e a segunda entrada é direta.
    cliques = [clique("criativo_B", id_="c1"), clique("criativo_A", id_="c2")]
    resultado = atribuir_entradas(
        [("a@s.whatsapp.net", None), ("b@s.whatsapp.net", None)], cliques
    )
    assert [r[2] for r in resultado] == ["ambigua", "direta"]


# ------------------------------------------------------------- permanência

def test_permanencia_em_minutos():
    agora = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)
    assert permanencia_em_minutos(agora - timedelta(minutes=90), agora) == 90


def test_permanencia_assume_utc_quando_a_data_vem_sem_fuso():
    # O PostgREST devolve timestamptz, mas uma linha antiga pode chegar naive —
    # e subtrair naive de aware levanta TypeError, derrubando o ciclo inteiro.
    agora = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)
    assert permanencia_em_minutos(datetime(2026, 9, 20, 11, 0), agora) == 60


def test_permanencia_desconhecida_quando_nao_ha_entrada():
    agora = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)
    assert permanencia_em_minutos(None, agora) is None


# ------------------------------------------------------- ciclo completo
# O caminho inteiro (diff -> pareamento -> escrita) com um repositório de
# mentira: é aqui que um erro de montagem do evento apareceria, e não nas
# funções puras acima.

class RepositorioFalso:
    disponivel = True

    def __init__(self, cliques=None):
        self.roster = []
        self.cliques = cliques or []
        self.eventos = []
        self.consumidos = []
        self.semeados = 0

    def carregar_roster(self, grupo_id):
        return list(self.roster)

    def semear_roster(self, grupo_id, participantes):
        for p in participantes:
            ident = identidade(p)
            self.roster.append(membro(chave(ident), ident[1], atribuicao="preexistente"))
        self.semeados = len(self.roster)
        return self.semeados

    def buscar_cliques(self, group_jid, desde):
        return [c for c in self.cliques if c.get("consumido_em") is None]

    def consumir_clique(self, clique_id, agora):
        self.consumidos.append(clique_id)
        for c in self.cliques:
            if c["id"] == clique_id:
                c["consumido_em"] = agora

    def registrar_entradas(self, membros, eventos):
        self.roster.extend(membros)
        self.eventos.extend(eventos)

    def registrar_saidas(self, grupo_id, jids, eventos):
        self.eventos.extend(eventos)
        self.roster = [m for m in self.roster if m.participante_jid not in jids]


def grupo():
    return WhatsAppGroup(
        id=GRUPO, group_id_api="120@g.us", name="Mãe Inteligente #001",
        invite_link="x", member_count=0, nicho_id="n1",
    )


def test_primeiro_ciclo_nao_registra_entrada_de_quem_ja_estava():
    # Sem isso, o dia da estreia mostraria o grupo inteiro entrando de uma vez.
    repo = RepositorioFalso()
    rastreador = RastreadorMembros(repo)

    stats = rastreador.sincronizar(grupo(), [participante("a@s.whatsapp.net")])

    assert stats == {"entradas": 0, "saidas": 0, "semeados": 1}
    assert repo.eventos == []


def test_entrada_depois_de_clique_fica_com_a_origem_do_anuncio():
    repo = RepositorioFalso(cliques=[
        {"id": "c1", "utm_content": "criativo_A", "utm_campaign": "Setembro", "consumido_em": None}
    ])
    rastreador = RastreadorMembros(repo)
    g = grupo()

    rastreador.sincronizar(g, [participante("a@s.whatsapp.net")])          # semeia
    stats = rastreador.sincronizar(g, [participante("a@s.whatsapp.net"),
                                       participante("b@s.whatsapp.net")])   # entra b

    assert stats["entradas"] == 1
    evento = repo.eventos[0]
    assert (evento.tipo, evento.participante_jid) == ("entrada", "b@s.whatsapp.net")
    assert (evento.anuncio, evento.campanha) == ("criativo_A", "Setembro")
    assert evento.atribuicao == "direta"
    assert repo.consumidos == ["c1"]      # o clique não pode servir duas vezes


def test_saida_herda_o_anuncio_de_quem_saiu():
    # O caso que motivou tudo: saber de qual anúncio veio quem foi embora.
    repo = RepositorioFalso(cliques=[
        {"id": "c1", "utm_content": "criativo_B", "utm_campaign": "Setembro", "consumido_em": None}
    ])
    rastreador = RastreadorMembros(repo)
    g = grupo()

    rastreador.sincronizar(g, [participante("a@s.whatsapp.net")])
    rastreador.sincronizar(g, [participante("a@s.whatsapp.net"), participante("b@s.whatsapp.net")])
    stats = rastreador.sincronizar(g, [participante("a@s.whatsapp.net")])   # b sai

    assert stats["saidas"] == 1
    saida = repo.eventos[-1]
    assert saida.tipo == "saida"
    assert saida.anuncio == "criativo_B"
    assert saida.permanencia_min is not None
    assert [m.participante_jid for m in repo.roster] == ["a@s.whatsapp.net"]


def test_falha_no_banco_nao_derruba_o_ciclo():
    # Rastreio é observabilidade; o balanceador é o que mantém os grupos no ar.
    class RepositorioQuebrado(RepositorioFalso):
        def carregar_roster(self, grupo_id):
            raise RuntimeError("supabase fora do ar")

    stats = RastreadorMembros(RepositorioQuebrado()).sincronizar(
        grupo(), [participante("a@s.whatsapp.net")]
    )
    assert stats == {"entradas": 0, "saidas": 0, "semeados": 0}
