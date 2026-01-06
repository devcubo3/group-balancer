# 🎯 Criar Primeiro Grupo - Dona Promo #001

## Pré-requisitos

Antes de criar o primeiro grupo, certifique-se de:

### 1. ✅ Atualizar o Schema do Supabase

**Execute o SQL em [ATUALIZAR_SUPABASE.md](ATUALIZAR_SUPABASE.md)** no SQL Editor do Supabase para adicionar os novos campos e criar a tabela de logs de API.

### 2. ✅ Configurar o arquivo .env

Copie `.env.example` para `.env` e preencha com suas credenciais:

```bash
cp .env.example .env
```

Edite o `.env` e configure:

```env
# Supabase (já configurado no .env.example)
SUPABASE_URL=https://gvtycxhzbzkrtbbwjcmy.supabase.co
SUPABASE_KEY=eyJhbGc...

# UAZAPI - VOCÊ PRECISA PREENCHER ESTES
WHATSAPP_API_URL=https://free.uazapi.com
WHATSAPP_API_TOKEN=seu_token_aqui
WHATSAPP_INSTANCE_ID=sua_instancia_aqui
```

**Onde encontrar suas credenciais UAZAPI:**
- Token e Instance ID: https://uazapi.com/dashboard
- Certifique-se que sua instância está **conectada** ao WhatsApp

### 3. ✅ Instalar Dependências

```bash
pip install -r requirements.txt
```

## Opção 1: Script Dedicado (Recomendado)

Use o script criado especialmente para criar o primeiro grupo:

```bash
python create_first_group.py
```

Este script:
- Cria o grupo "Dona Promo #001"
- Salva no Supabase com todos os campos da API
- Registra logs de todas as chamadas à API
- Mostra um resumo completo do grupo criado

## Opção 2: Comando do Main.py

Você também pode usar o comando padrão:

```bash
python main.py create-group --group-name "Dona Promo #001" --group-number 1
```

## O Que Acontece Quando Você Executa

1. **Chamada à API UAZAPI** - POST /group/create
   - Nome: "Dona Promo #001"
   - Participantes: [seu número de admin]

2. **Extração de Dados**
   - JID do grupo (ex: 120363123456789@g.us)
   - Subject (nome do grupo)
   - Owner JID (criador)
   - Timestamps e metadados

3. **Obtenção do Link de Convite** - POST /group/info
   - Link de convite do grupo

4. **Salvamento no Supabase**
   - Tabela `whatsapp_groups`: Dados do grupo
   - Tabela `api_call_logs`: Logs de todas as chamadas à API

## Verificar Se Funcionou

### No Terminal

Você verá uma mensagem como:

```
============================================================
✅ GRUPO CRIADO COM SUCESSO!
============================================================

📋 Detalhes do Grupo:
   Nome: Dona Promo #001
   ID (JID): 120363123456789@g.us
   Link de Convite: https://chat.whatsapp.com/xxxxx
   Membros: 1
   Ativo: Sim
   Assunto: Dona Promo #001
   Dono: 5533987610311@s.whatsapp.net

✓ Grupo salvo no Supabase com sucesso!
✓ Logs de API salvos no banco de dados!
============================================================
```

### No Supabase

Vá em "Table Editor" e verifique:

**Tabela `whatsapp_groups`:**
```sql
SELECT * FROM whatsapp_groups;
```

Você verá o grupo "Dona Promo #001" com todos os campos preenchidos.

**Tabela `api_call_logs`:**
```sql
SELECT endpoint, method, success, status_code FROM api_call_logs;
```

Você verá os logs das chamadas:
- POST /group/create (criar grupo)
- POST /group/info (buscar link de convite)

## Troubleshooting

### ❌ Erro: "ModuleNotFoundError"

```bash
pip install -r requirements.txt
```

### ❌ Erro: "Erro HTTP na API WhatsApp: 401"

Seu token está incorreto. Verifique:
1. Se você copiou o token corretamente no `.env`
2. Se o token é válido no dashboard da UAZAPI

### ❌ Erro: "Erro HTTP na API WhatsApp: 403"

Sua instância não está conectada. Acesse o dashboard da UAZAPI e conecte sua instância ao WhatsApp.

### ❌ Erro: "API não retornou JID do grupo"

A resposta da API está em um formato diferente. Execute:

```bash
python test_uazapi.py
```

E verifique a estrutura da resposta.

### ❌ Erro: "Erro ao criar grupo no Supabase"

Verifique se você executou o SQL de atualização em [ATUALIZAR_SUPABASE.md](ATUALIZAR_SUPABASE.md).

## Próximos Passos

Após criar o primeiro grupo, você pode:

### 1. Testar o Load Balancer

```bash
python main.py get-best-group
```

Deve retornar o grupo "Dona Promo #001" como o melhor para receber novos leads.

### 2. Iniciar o Monitor

```bash
python main.py monitor
```

O monitor vai verificar o grupo a cada 60 segundos e criar novos grupos automaticamente quando necessário.

### 3. Ver os Logs

**No Supabase:**

```sql
-- Ver logs de monitoramento
SELECT * FROM monitor_logs ORDER BY checked_at DESC LIMIT 10;

-- Ver logs de API
SELECT * FROM api_call_logs ORDER BY called_at DESC LIMIT 10;

-- Estatísticas de chamadas
SELECT
    endpoint,
    COUNT(*) as total,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) as success,
    AVG(duration_ms)::INT as avg_ms
FROM api_call_logs
GROUP BY endpoint;
```

## Campos Salvos no Banco

Quando você cria um grupo, os seguintes dados são salvos:

### Campos Principais
- `group_id_api` - JID do grupo (120363123456789@g.us)
- `name` - Nome do grupo
- `invite_link` - Link de convite
- `member_count` - Número de membros
- `is_active` - Se está ativo

### Campos da API UAZAPI
- `subject` - Assunto/nome do grupo
- `description` - Descrição
- `owner_jid` - JID do criador
- `created_timestamp` - Timestamp de criação
- `is_announcement` - Se é grupo de anúncios
- `is_locked` - Se está bloqueado
- `is_parent` - Se é grupo pai de comunidade
- `linked_parent_jid` - JID do grupo pai (se for subcomunidade)

Todos esses campos são preenchidos automaticamente com os dados retornados pela API UAZAPI!
