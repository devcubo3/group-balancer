# Arquitetura do Sistema

## Visão Geral

```
┌─────────────────────────────────────────────────────────────┐
│                    FLUXO DO SISTEMA                          │
└─────────────────────────────────────────────────────────────┘

┌──────────┐       ┌──────────────┐       ┌─────────────┐
│   LEAD   │──────▶│ Load Balancer│──────▶│ Grupo Ideal │
│  (Click) │       │  (Algoritmo)  │       │  (< 900)    │
└──────────┘       └──────────────┘       └─────────────┘
                           │
                           ▼
                   ┌──────────────┐
                   │  Supabase DB │
                   │ (Grupos)     │
                   └──────────────┘
                           ▲
                           │
                   ┌──────────────┐
                   │   Monitor    │◀──── Verifica a cada 60s
                   │ (Tempo Real) │
                   └──────────────┘
                           │
                           ▼
        ┌──────────────────────────────────┐
        │ Grupo atual ≥ 950 membros?       │
        └──────────────────────────────────┘
                   │           │
              ✅ SIM       ❌ NÃO
                   │           │
                   ▼           ▼
          ┌──────────────┐  Continue
          │ CRIAR NOVO   │  monitorando
          │    GRUPO     │
          └──────────────┘
                   │
                   ▼
          ┌──────────────┐
          │WhatsApp API  │
          │(UAZAPI)      │
          └──────────────┘
```

## Componentes Principais

### 1. Load Balancer (`load_balancer.py`)

**Responsabilidades**:
- Algoritmo de distribuição de leads
- Auto-scaling (criação de novos grupos)
- Sincronização de membros

**Métodos Principais**:
```python
get_best_group_for_lead()      # Busca melhor grupo (< 900 membros)
should_scale_out(group)        # Verifica se precisa criar novo (≥ 950)
create_new_group()             # Cria grupo via API + salva no DB
sync_all_groups()              # Daily sync de todos os grupos
```

### 2. Monitor (`monitor.py`)

**Responsabilidades**:
- Loop contínuo de verificação
- Trigger de auto-scaling
- Agendamento de sync diária

**Processos**:
```python
# Processo A: Tempo Real (a cada 60s)
check_newest_group() → sync_group_members() → should_scale_out() → create_new_group()

# Processo B: Daily Sync (a cada 24h)
daily_sync() → sync_all_groups() → atualiza todos os member_count
```

### 3. Supabase Client (`supabase_client.py`)

**Responsabilidades**:
- CRUD de grupos no banco
- Queries otimizadas

**Métodos Principais**:
```python
get_active_groups()                    # Lista todos ativos
get_newest_group()                     # Busca mais recente (ORDER BY created_at DESC)
get_best_group_for_redirect(max=900)  # Algoritmo: menor member_count < 900
create_group(group)                    # Insere novo grupo
update_member_count(id, count)         # Atualiza contagem
```

### 4. WhatsApp Service (`whatsapp_service.py`)

**Responsabilidades**:
- Comunicação com API UAZAPI
- Rate limit protection

**Métodos Principais**:
```python
create_group(name)              # POST /groups/create
get_group_info(group_id)        # GET /groups/{id}/info
get_group_members_count(id)     # Extrai count do get_group_info
get_group_invite_link(id)       # GET /groups/{id}/invite-link
wait_rate_limit()               # Sleep de 2s entre chamadas
```

## Fluxo de Dados Detalhado

### Cenário 1: Novo Lead Clica no Link

```
1. Lead clica no redirector
2. Redirector chama: load_balancer.get_best_group_for_lead()
3. Load Balancer consulta Supabase:
   SELECT * FROM whatsapp_groups
   WHERE is_active = true AND member_count < 900
   ORDER BY member_count ASC
   LIMIT 1
4. Retorna grupo com link de convite
5. Lead é redirecionado: https://chat.whatsapp.com/XXXXX
```

### Cenário 2: Monitor Detecta Scale-Out

```
1. Monitor executa check_newest_group()
2. Busca grupo mais novo: SELECT * ... ORDER BY created_at DESC LIMIT 1
3. Chama WhatsApp API: GET /groups/{id}/info
4. Recebe: { participants: [...950 membros...] }
5. Atualiza DB: UPDATE whatsapp_groups SET member_count = 950
6. Verifica: if member_count >= 950 → TRIGGER!
7. Cria novo grupo:
   a) POST /groups/create → Recebe group_id
   b) GET /groups/{id}/invite-link → Recebe link
   c) INSERT INTO whatsapp_groups (...)
8. Próximos leads vão para o novo grupo
```

### Cenário 3: Sincronização Diária

```
1. Schedule dispara daily_sync() às 00:00
2. Busca todos grupos ativos: SELECT * WHERE is_active = true
3. Para cada grupo:
   a) GET /groups/{id}/info via API
   b) Extrai member_count
   c) UPDATE whatsapp_groups SET member_count = X
   d) Sleep 2s (rate limit)
4. Log final: X atualizados, Y sem alteração, Z falhas
```

## Regras de Negócio Implementadas

| Regra | Valor | Onde está implementado |
|-------|-------|------------------------|
| Limite WhatsApp | 1000 | `config.py:19` (documentação) |
| Threshold Scale-Out | 950 | `config.py:18` + `load_balancer.py:42` |
| Limite Redirect | 900 | `config.py:17` + `load_balancer.py:27` |
| Algoritmo Distribuição | Menor `membros_atuais` dentro do nicho | `supabase_client.py` (`get_best_group_for_redirect`) |
| Check Interval | 60s | `config.py:22` + `monitor.py:76` |
| Daily Sync | 24h | `config.py:23` + `monitor.py:84` |
| Rate Limit Delay | 2s | `config.py:24` + `whatsapp_service.py:175` |

## Uma cadeia de overflow por nicho

O ecossistema é multi-nicho. `controle_grupos.nicho_id` diz qual nicho cada grupo atende, e
`ordem_sequencial` é **por nicho** — "Bebês e Crianças #001" e "Geral #001" coexistem.

Consequências no código:

- `get_active_groups(nicho_id)`, `get_newest_group(nicho_id)` e `get_best_group_for_redirect(max, nicho_id)`
  são escopados por nicho
- `create_group(group, nicho_id)` calcula a `ordem_sequencial` contando só os grupos daquele nicho
- `monitor.check_newest_group()` itera os nichos ativos e avalia o scale-out de cada cadeia
  separadamente. **Um único processo atende todos os nichos** — um nicho novo é uma linha na tabela
  `nichos`, não um deploy novo
`main.py` e `create_first_group.py` aceitam `--nicho <slug>`. Sem o parâmetro, as operações valem
para todos os nichos (ou caem no Geral, no caso de criação).

### Identidade dos grupos (nome, descrição e foto)

Cada nicho define a cara dos seus grupos, em colunas de `nichos`:

| Coluna | Uso | Fallback |
|---|---|---|
| `nome_grupo` | Prefixo do nome: `"Caramelo Bebê"` → `"Caramelo Bebê #001"` | `nichos.nome` |
| `descricao_grupo` | Descrição aplicada na criação | env `GROUP_DESCRIPTION` |
| `imagem_url` | Foto do grupo | env `GROUP_IMAGE_URL` |

As env vars `GROUP_DESCRIPTION` e `GROUP_IMAGE_URL` continuam existindo, mas viraram **apenas
fallback**. Enquanto eram a única fonte, todo nicho herdaria a mesma descrição e a mesma foto —
o oposto do que nichar significa. Com a identidade no banco, mudá-la é um `UPDATE`, sem deploy.

O sufixo `#NNN` é obrigatório no nome: `monitor.py` extrai o número com `re.search(r'#(\d+)', ...)`
para calcular o próximo grupo da cadeia. Um nome sem esse padrão faz o balancer cair no fallback de
contar os grupos do nicho.

## Banco de Dados - Tabela `controle_grupos`

> A tabela real deste projeto é `controle_grupos`, com nomes de coluna em português. O arquivo
> `supabase_setup_completo.sql` cria uma tabela `whatsapp_groups` que **não existe no banco e não é
> usada pelo código** — SQL morto, mantido apenas por histórico.
>
> `_map_group()` em `supabase_client.py` é a única ponte entre os nomes do banco e os nomes da API
> UAZAPI usados no modelo `WhatsAppGroup`.

```sql
┌──────────────────┬──────────┬────────────────────────────────────────┐
│ Campo            │ Tipo     │ Descrição                              │
├──────────────────┼──────────┼────────────────────────────────────────┤
│ id               │ UUID     │ PK                                     │
│ nicho_id         │ UUID     │ FK → nichos. NOT NULL, default 'geral' │
│ group_jid        │ TEXT     │ JID do WhatsApp (unique)               │
│ instance_name    │ TEXT     │ Número da instância UazAPI             │
│ subject          │ TEXT     │ Nome do grupo, ex: "Geral #001"        │
│ link_convite     │ TEXT     │ URL do convite                         │
│ membros_atuais   │ INTEGER  │ Quantidade de membros                  │
│ capacidade_max   │ INTEGER  │ Capacidade (default 800)               │
│ status           │ TEXT     │ 'ativo' | 'cheio' | 'arquivado'        │
│ ordem_sequencial │ INTEGER  │ Posição na cadeia DO NICHO             │
│ created_at       │ TIMESTAMP│ Data de criação                        │
└──────────────────┴──────────┴────────────────────────────────────────┘

Não existe coluna `updated_at`.

Índices:
- controle_grupos_group_jid_key (group_jid, unique)
- controle_grupos_nicho_idx (nicho_id, status, ordem_sequencial)
```

## Segurança e Rate Limiting

### Rate Limiting
- Delay de 2s entre chamadas consecutivas
- Timeout de 30s por requisição
- Proteção contra bloqueio da API

### Tratamento de Erros
- Try/catch em todas as chamadas API
- Logs detalhados de erros
- Continuidade do sistema em caso de falha pontual

### Variáveis Sensíveis
- Tokens e keys no `.env` (não versionado)
- `.gitignore` protege credenciais
- Supabase RLS pode ser habilitado

## Comandos CLI

```bash
# Produção
python main.py monitor                          # Loop infinito com auto-scaling (todos os nichos)

# Manutenção
python main.py sync                             # Força sync de todos os grupos
python main.py create-group --nicho bebes       # Adiciona grupo à cadeia de um nicho
python create_first_group.py --nicho bebes      # Cria o primeiro grupo de um nicho

# Descoberta de fontes
python main.py list-groups                      # Lista os grupos da instância com JID,
                                                # marcando quais já estão em `fontes`

# Debug
python main.py get-best-group --nicho bebes     # Testa o algoritmo dentro de um nicho
python main.py test                             # Testa conexões e lista nichos
```

### Descobrindo o JID de um grupo-fonte

Ao entrar num grupo novo para monitorar, é preciso o JID dele para cadastrar em `fontes`.
`list-groups` resolve isso: usa `WHATSAPP_API_TOKEN`, então **precisa ser o token da instância que
está nos grupos de origem** — que pode não ser a mesma usada para publicar.

Alternativa sem credencial: `filtrobot/fontes.py` loga em nível INFO todo grupo desconhecido que
manda mensagem (`Fonte não cadastrada (whatsapp/<JID>) — roteando para o nicho Geral`). Basta olhar
o log do webhook depois que uma oferta cair no grupo.

## Logs e Monitoramento

### Níveis de Log
- **INFO**: Operações normais (grupo criado, sync concluído)
- **WARNING**: Alertas (grupo atingiu threshold, nenhum disponível)
- **ERROR**: Falhas (API não respondeu, erro de conexão)
- **DEBUG**: Detalhes técnicos (requisições, queries)

### Saídas
- **Console**: Stdout em tempo real
- **Arquivo**: `logs/monitor.log` (persistente)

### Exemplo de Log
```
2026-01-05 21:30:00 [INFO] 🔍 VERIFICAÇÃO AUTOMÁTICA
2026-01-05 21:30:01 [INFO] ✓ Grupo mais novo: Grupo 5 (920 membros)
2026-01-05 21:30:02 [INFO] ✓ Sistema OK
2026-01-05 22:00:00 [WARNING] 🚨 SCALE-OUT TRIGGER: Grupo 5 atingiu 952 membros
2026-01-05 22:00:05 [INFO] ✅ NOVO GRUPO CRIADO: Grupo 6
```

## Próximas Melhorias Possíveis

- [ ] Dashboard web para visualização
- [ ] Alertas via Telegram/Discord
- [ ] Backup automático de grupos
- [ ] Estatísticas detalhadas (taxa de crescimento)
- [ ] API REST para integração externa
- [ ] Docker container para deploy
- [ ] Health check endpoint
- [ ] Métricas Prometheus/Grafana

---

**Sistema pronto para integração final com a API UAZAPI!**
