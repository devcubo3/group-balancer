"""
Servidor do painel de grupos.

Roda numa thread daemon ao lado do loop do monitor, na mesma aplicação: o painel
mostra exatamente o que este processo escreve, então separá-lo em outro deploy só
criaria duas coisas para manter no ar em vez de uma.

Serve um arquivo estático (painel/index.html) com três valores injetados a partir
do .env em tempo de resposta:

- SUPABASE_URL / SUPABASE_KEY — para a chave não ficar hardcoded no repositório
- SCALE_OUT_THRESHOLD — para a marca no medidor de capacidade ser o gatilho real
  deste deploy, e não o padrão do código

Os dados vêm do PostgREST direto do navegador, pelas views painel_grupos,
painel_fluxo_diario e painel_saude_monitor. Este servidor não consulta o banco.
"""
import hmac
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from .config import settings

logger = logging.getLogger(__name__)

PAINEL_HTML = Path(__file__).resolve().parent.parent / "painel" / "index.html"


def _render() -> bytes:
    """Lê o HTML e injeta a configuração. Lido a cada resposta: o arquivo é
    pequeno e assim editar o painel não exige reiniciar o monitor."""
    html = PAINEL_HTML.read_text(encoding="utf-8")
    return (
        html.replace("__SUPABASE_URL__", settings.supabase_url)
            .replace("__SUPABASE_KEY__", settings.supabase_key)
            .replace("__SCALE_OUT__", str(settings.scale_out_threshold))
    ).encode("utf-8")


def _autorizado(handler: BaseHTTPRequestHandler, query: dict) -> bool:
    """Sem PAINEL_TOKEN configurado o painel é aberto. Com ele, exige
    ?t=<token> ou o header X-Painel-Token."""
    esperado = settings.painel_token
    if not esperado:
        return True
    recebido = (query.get("t") or [""])[0] or handler.headers.get("X-Painel-Token", "")
    return hmac.compare_digest(recebido, esperado)


class _Handler(BaseHTTPRequestHandler):
    server_version = "GroupBalancerPainel/1.0"

    def _responde(self, status: int, corpo: bytes, tipo: str = "text/html; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        # O painel carrega credencial do Supabase; nenhum intermediário deve guardá-lo.
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(corpo)

    def do_GET(self):
        url = urlparse(self.path)
        query = parse_qs(url.query)

        # Endpoint de liveness para o Dokploy, sempre aberto.
        if url.path == "/healthz":
            self._responde(200, b"ok", "text/plain; charset=utf-8")
            return

        if url.path not in ("/", "/index.html", "/painel", "/painel/"):
            self._responde(404, b"404", "text/plain; charset=utf-8")
            return

        if not _autorizado(self, query):
            self._responde(
                401,
                "<!doctype html><meta charset=utf-8><title>Painel</title>"
                "<p style='font:15px system-ui;padding:24px'>Token inválido ou ausente. "
                "Acesse com <code>?t=SEU_TOKEN</code>.</p>".encode("utf-8"),
            )
            return

        try:
            self._responde(200, _render())
        except FileNotFoundError:
            logger.error("✗ painel/index.html não encontrado em %s", PAINEL_HTML)
            self._responde(500, b"painel/index.html ausente no build", "text/plain; charset=utf-8")

    do_HEAD = do_GET

    def log_message(self, fmt, *args):
        # O default do http.server escreve direto em stderr, fora do logging.
        logger.debug("painel %s", fmt % args)


def iniciar_em_thread() -> bool:
    """
    Sobe o painel numa thread daemon. Devolve False se não subir.

    Nunca derruba o monitor: o painel é observabilidade, e um painel fora do ar
    é muito menos grave que um balancer fora do ar.
    """
    if not PAINEL_HTML.exists():
        logger.warning("⚠ painel/index.html não encontrado — painel não será servido")
        return False

    try:
        servidor = ThreadingHTTPServer(("0.0.0.0", settings.painel_port), _Handler)
    except OSError as e:
        logger.error(f"✗ Painel não subiu na porta {settings.painel_port}: {e}")
        return False

    threading.Thread(target=servidor.serve_forever, name="painel", daemon=True).start()

    if settings.painel_token:
        logger.info(f"📊 Painel em :{settings.painel_port} (protegido por PAINEL_TOKEN)")
    else:
        logger.warning(
            f"📊 Painel em :{settings.painel_port} — ABERTO. "
            "Defina PAINEL_TOKEN para exigir ?t=<token>."
        )
    return True
