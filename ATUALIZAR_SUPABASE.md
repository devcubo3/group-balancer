# Instruções para Atualizar o Schema do Supabase

## ⚠️ IMPORTANTE - Execute ANTES de criar o primeiro grupo

Antes de executar o script para criar o grupo "Dona Promo #001", você precisa atualizar o schema do banco de dados Supabase com os novos campos.

## Passo 1: Acessar o Supabase

1. Acesse https://supabase.com
2. Faça login no seu projeto
3. Vá em "SQL Editor" no menu lateral

## Passo 2: Executar o SQL de Atualização

Cole e execute o SQL abaixo para adicionar os novos campos à tabela existente:

```sql
-- ============================================
-- ADICIONAR NOVOS CAMPOS À TABELA whatsapp_groups
-- ============================================

ALTER TABLE whatsapp_groups
ADD COLUMN IF NOT EXISTS subject TEXT,
ADD COLUMN IF NOT EXISTS description TEXT,
ADD COLUMN IF NOT EXISTS owner_jid TEXT,
ADD COLUMN IF NOT EXISTS created_timestamp BIGINT,
ADD COLUMN IF NOT EXISTS participant_version_id TEXT,
ADD COLUMN IF NOT EXISTS is_announcement BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS is_locked BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS is_parent BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS default_membership_approval_mode BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS is_incognito BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS linked_parent_jid TEXT;

-- ============================================
-- CRIAR TABELA DE LOGS DE CHAMADAS API
-- ============================================

CREATE TABLE IF NOT EXISTS api_call_logs (
    -- Identificador único do log
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

    -- Endpoint chamado (ex: /group/create, /group/info, /group/list)
    endpoint TEXT NOT NULL,

    -- Método HTTP (GET, POST, PUT, DELETE)
    method TEXT NOT NULL CHECK (method IN ('GET', 'POST', 'PUT', 'DELETE', 'PATCH')),

    -- Payload enviado na requisição (JSON)
    request_payload JSONB,

    -- Resposta completa da API (JSON)
    response_data JSONB,

    -- Código de status HTTP (200, 400, 500, etc)
    status_code INTEGER,

    -- Se a chamada foi bem sucedida
    success BOOLEAN DEFAULT false,

    -- Mensagem de erro (se houver)
    error_message TEXT,

    -- Duração da chamada em milissegundos
    duration_ms INTEGER,

    -- ID do grupo relacionado (se aplicável)
    group_id_api TEXT,

    -- Timestamp da chamada
    called_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- Índices para api_call_logs
CREATE INDEX IF NOT EXISTS idx_api_logs_endpoint
ON api_call_logs(endpoint);

CREATE INDEX IF NOT EXISTS idx_api_logs_group_id
ON api_call_logs(group_id_api);

CREATE INDEX IF NOT EXISTS idx_api_logs_called_at
ON api_call_logs(called_at DESC);

CREATE INDEX IF NOT EXISTS idx_api_logs_success
ON api_call_logs(success);

CREATE INDEX IF NOT EXISTS idx_api_logs_errors
ON api_call_logs(success)
WHERE success = false;

-- ============================================
-- CONFIRMAÇÃO
-- ============================================

SELECT 'Schema atualizado com sucesso!' as status;
```

## Passo 3: Verificar a Atualização

Execute esta query para verificar se as colunas foram adicionadas:

```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'whatsapp_groups'
ORDER BY ordinal_position;
```

Você deve ver os novos campos:
- subject
- description
- owner_jid
- created_timestamp
- participant_version_id
- is_announcement
- is_locked
- is_parent
- default_membership_approval_mode
- is_incognito
- linked_parent_jid

## Passo 4: Verificar Tabela de Logs

```sql
SELECT * FROM api_call_logs LIMIT 1;
```

Se não der erro, a tabela foi criada com sucesso!

## Próximos Passos

Após executar o SQL acima, você pode:

1. Configurar o arquivo `.env` com suas credenciais
2. Executar o script para criar o primeiro grupo:
   ```bash
   python create_first_group.py
   ```

Ou usar o comando do main.py:
```bash
python main.py create-group --group-name "Dona Promo #001" --group-number 1
```

## Consultas Úteis

### Ver todos os grupos criados
```sql
SELECT 
    name,
    group_id_api,
    member_count,
    subject,
    owner_jid,
    is_active,
    created_at
FROM whatsapp_groups
ORDER BY created_at DESC;
```

### Ver logs de chamadas à API
```sql
SELECT 
    endpoint,
    method,
    status_code,
    success,
    duration_ms,
    called_at
FROM api_call_logs
ORDER BY called_at DESC
LIMIT 20;
```

### Ver estatísticas de chamadas por endpoint
```sql
SELECT
    endpoint,
    method,
    COUNT(*) as total_calls,
    SUM(CASE WHEN success = true THEN 1 ELSE 0 END) as successful,
    SUM(CASE WHEN success = false THEN 1 ELSE 0 END) as failed,
    AVG(duration_ms)::INTEGER as avg_duration_ms
FROM api_call_logs
GROUP BY endpoint, method
ORDER BY total_calls DESC;
```
