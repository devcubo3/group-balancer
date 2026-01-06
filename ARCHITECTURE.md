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
| Algoritmo Distribuição | Menor member_count | `supabase_client.py:55` (ORDER BY) |
| Check Interval | 60s | `config.py:22` + `monitor.py:76` |
| Daily Sync | 24h | `config.py:23` + `monitor.py:84` |
| Rate Limit Delay | 2s | `config.py:24` + `whatsapp_service.py:175` |

## Banco de Dados - Tabela `whatsapp_groups`

```sql
┌──────────────┬─────────┬──────────────────────────┐
│ Campo        │ Tipo    │ Descrição                │
├──────────────┼─────────┼──────────────────────────┤
│ id           │ UUID    │ PK                       │
│ group_id_api │ TEXT    │ ID do WhatsApp (unique)  │
│ name         │ TEXT    │ Ex: "Grupo 101"          │
│ invite_link  │ TEXT    │ URL do convite           │
│ member_count │ INTEGER │ Quantidade de membros    │
│ is_active    │ BOOLEAN │ Ativo/Desativado         │
│ created_at   │ TIMESTAMP│ Data criação           │
│ updated_at   │ TIMESTAMP│ Última atualização     │
└──────────────┴─────────┴──────────────────────────┘

Índices:
- idx_groups_active (is_active)
- idx_groups_member_count (member_count)
- idx_groups_created_at (created_at DESC)
- idx_groups_load_balancer (is_active, member_count)
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
python main.py monitor          # Loop infinito com auto-scaling

# Manutenção
python main.py sync             # Força sync de todos os grupos
python main.py create-group     # Cria grupo manualmente

# Debug
python main.py get-best-group   # Testa algoritmo
python main.py test             # Testa conexões

# Desenvolvimento
python main.py test             # Valida setup inicial
```

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
