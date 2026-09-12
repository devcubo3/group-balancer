"""
Configuração de testes.

`src.config` instancia `Settings()` no import e SUPABASE_URL/SUPABASE_KEY são
obrigatórios, então eles precisam existir antes de qualquer import de `src.*`.
Valores fake: nenhum teste desta suíte toca o Supabase de verdade.
"""
import os

os.environ.setdefault("SUPABASE_URL", "https://teste.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "chave-de-teste")
