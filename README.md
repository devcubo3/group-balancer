# WhatsApp Group Load Balancer & Auto-Scaling System

Sistema inteligente de monitoramento e automação de grupos de WhatsApp para distribuição eficiente de leads.

## Funcionalidades

- **Load Balancer Inteligente**: Distribui leads automaticamente para o grupo com menor número de membros
- **Auto-Scaling**: Cria novos grupos automaticamente quando o threshold é atingido
- **Monitor em Tempo Real**: Verifica continuamente o grupo mais recente (a cada 60s)
- **Monitor Diário**: Atualiza a contagem de membros de TODOS os grupos (1x por dia)
- **Sincronização Completa**: Sincronização geral a cada 12 horas
- **Rate Limit Protection**: Delay automático entre chamadas para evitar bloqueios
- **Logs Detalhados**: Rastreamento completo de todas as operações

## 🚀 Novidade: Sistema de Monitoramento Duplo

O sistema agora possui **2 monitores** que trabalham em conjunto:

### 1️⃣ Monitor Principal (Grupo Mais Novo)
- **Arquivo**: `main.py`
- **Frequência**: Contínuo (a cada 60 segundos)
- **Foco**: Apenas o grupo MAIS NOVO
- **Objetivo**: Criar novo grupo quando atingir 950 membros

### 2️⃣ Monitor Diário (Todos os Grupos)
- **Arquivo**: `daily_monitor.py`
- **Frequência**: 1x por dia (execução agendada)
- **Foco**: TODOS os grupos ativos
- **Objetivo**: Manter contagens atualizadas e não deixar grupos para trás

📖 **Documentação completa**: [MONITOR_DIARIO.md](MONITOR_DIARIO.md)

## Regras de Negócio

- **Limite Máximo Real**: 1000 usuários (limite do WhatsApp)
- **Gatilho de Criação (Scale-out)**: Quando o grupo atual atingir **950 usuários**
- **Limite de Redirecionamento**: Apenas grupos com até **900 usuários** recebem novos leads
- **Prioridade**: Sempre busca o grupo com **menor número de usuários**

## Estrutura do Projeto

```
group-balancer/
├── src/
│   ├── __init__.py
│   ├── config.py              # Configurações e variáveis de ambiente
│   ├── models.py              # Modelos de dados (Pydantic)
│   ├── supabase_client.py     # Cliente para interação com Supabase
│   ├── whatsapp_service.py    # Serviço para API do WhatsApp (UAZAPI)
│   ├── load_balancer.py       # Algoritmo de distribuição e auto-scaling
│   └── monitor.py             # Monitor de grupos (contínuo + diário)
├── main.py                    # Monitor principal (grupo mais novo)
├── daily_monitor.py           # Monitor diário (todos os grupos)
├── integrated_monitor.py      # Monitor integrado (OPCIONAL)
├── requirements.txt           # Dependências Python
├── .env.example              # Template de variáveis de ambiente
├── MONITOR_DIARIO.md         # Documentação do monitor diário
└── README.md                 # Este arquivo
```

## Instalação

### 1. Clone o repositório

```bash
cd group-balancer
```

### 2. Crie um ambiente virtual

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Configure as variáveis de ambiente

Copie o arquivo `.env.example` para `.env`:

```bash
cp .env.example .env
```

Edite o arquivo `.env` e preencha com suas credenciais:

```env
# Supabase
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=sua_chave_aqui

# WhatsApp API (UAZAPI)
WHATSAPP_API_URL=https://api.uazapi.com
WHATSAPP_API_TOKEN=seu_token_aqui
WHATSAPP_INSTANCE_ID=sua_instancia_aqui
```

### 5. Crie a tabela no Supabase

Execute o seguinte SQL no Supabase:

```sql
CREATE TABLE whatsapp_groups (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    group_id_api TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    invite_link TEXT NOT NULL,
    member_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- Índices para melhor performance
CREATE INDEX idx_groups_active ON whatsapp_groups(is_active);
CREATE INDEX idx_groups_member_count ON whatsapp_groups(member_count);
CREATE INDEX idx_groups_created_at ON whatsapp_groups(created_at DESC);
```

## Uso

### Comandos Disponíveis

#### 1. Monitor Principal (Grupo Mais Novo)

Inicia o monitor contínuo que verifica o grupo mais novo a cada 60 segundos:

```bash
python main.py monitor
```

Este comando irá:
- Verificar o grupo mais novo a cada 60 segundos (configurável)
- Criar novo grupo automaticamente quando atingir 950 membros
- Executar sincronização a cada 12 horas
- Rodar indefinidamente até você pressionar Ctrl+C

#### 2. Monitor Diário (Todos os Grupos)

Executa uma verificação única de TODOS os grupos ativos:

```bash
python daily_monitor.py
```

Este comando irá:
- Buscar todos os grupos ativos do Supabase
- Sincronizar a contagem de membros de cada grupo com a API
- Aguardar 2 segundos entre cada chamada (evitar rate limit)
- Salvar logs detalhados no banco de dados
- Finalizar após processar todos os grupos

**Recomendação**: Agendar para executar 1x por dia (Task Scheduler/Cron)

#### 3. Monitor Integrado (OPCIONAL)

Executa ambos os monitores em um único processo:

```bash
python integrated_monitor.py
```

Este comando combina:
- Monitor contínuo do grupo mais novo (a cada 60s)
- Monitor diário completo (agendado para às 3h da manhã)
- Sincronização a cada 12 horas

#### 4. Sincronização Manual

Sincroniza a contagem de membros de todos os grupos ativos:

```bash
python main.py sync
```

#### 5. Criar Grupo Manualmente

Cria um novo grupo via API:

```bash
# Cria próximo grupo automaticamente (ex: Grupo 101)
python main.py create-group

# Cria grupo com número específico
python main.py create-group --group-number 105
```

#### 6. Testar Algoritmo de Load Balancer

Verifica qual seria o melhor grupo para receber um novo lead:

```bash
python main.py get-best-group
```

#### 7. Testar Conexões

Testa conectividade com Supabase e WhatsApp API:

```bash
python main.py test
```

## Configuração Avançada

Você pode ajustar os parâmetros no arquivo `.env`:

```env
# Limite para redirecionamento (padrão: 900)
MAX_MEMBERS_FOR_REDIRECT=900

# Threshold para criar novo grupo (padrão: 950)
SCALE_OUT_THRESHOLD=950

# Intervalo de verificação em segundos (padrão: 60)
MONITOR_CHECK_INTERVAL=60

# Intervalo de sincronização diária em horas (padrão: 24)
DAILY_SYNC_INTERVAL=24

# Delay entre chamadas API em segundos (padrão: 2)
API_CALL_DELAY=2

# Timeout de requisições em segundos (padrão: 30)
API_TIMEOUT=30

# Nível de log (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO
```

## ⏰ Agendamento do Monitor Diário

### Windows (Task Scheduler)

1. Abrir "Agendador de Tarefas" (Task Scheduler)
2. Criar Nova Tarefa
3. Configurar:
   - **Nome**: Monitor Diário Grupos WhatsApp
   - **Descrição**: Atualiza contagem de membros de todos os grupos
   - **Gatilho**: Diariamente às 03:00
   - **Ação**: Iniciar programa
     - **Programa**: `python`
     - **Argumentos**: `daily_monitor.py`
     - **Diretório**: `C:\Users\davin\OneDrive\Projetos\group-balancer`

### Linux/Mac (Cron)

```bash
# Editar crontab
crontab -e

# Adicionar linha (executa todo dia às 3h)
0 3 * * * cd /caminho/para/group-balancer && python daily_monitor.py >> logs/daily_monitor.log 2>&1
```

### Alternativa: Usar Monitor Integrado

Se preferir não usar agendador externo, use o `integrated_monitor.py` que faz tudo em um único processo:

```bash
python integrated_monitor.py
```

Isso executa:
- Monitor contínuo do grupo mais novo (a cada 60s)
- Monitor diário completo (às 3h da manhã)
- Sincronização a cada 12 horas

## Integração com Redirector

Para integrar com seu sistema de redirecionamento, crie um endpoint que consulte o melhor grupo:

```python
from src.load_balancer import LoadBalancer

def redirect_lead():
    lb = LoadBalancer()
    result = lb.get_best_group_for_lead()

    if result.group:
        # Redireciona para o link do grupo
        return result.group.invite_link
    else:
        # Nenhum grupo disponível, criar novo ou mostrar erro
        new_group = lb.create_new_group()
        return new_group.invite_link if new_group else "erro"
```

## API do WhatsApp (UAZAPI)

O sistema foi preparado para funcionar com a API UAZAPI. Você precisará ajustar os endpoints em `src/whatsapp_service.py` conforme a documentação específica da sua API.

### Endpoints que precisam ser ajustados:

1. `create_group()` - Criar grupo
2. `get_group_info()` - Obter informações do grupo
3. `get_group_invite_link()` - Obter link de convite

Cada método está marcado com comentários `# AJUSTAR ENDPOINT` para facilitar a customização.

## Logs

Os logs são salvos em:
- **Console**: Saída padrão (stdout)
- **Arquivo**: `logs/monitor.log` (configurável)

## Troubleshooting

### Erro: "Nenhum grupo encontrado"

Execute o comando para criar o primeiro grupo:

```bash
python main.py create-group --group-number 1
```

### Erro: "Falha ao conectar com Supabase"

Verifique:
- URL do Supabase está correta
- Chave de API tem permissões necessárias
- Tabela `whatsapp_groups` foi criada

### Erro: "API WhatsApp não responde"

Verifique:
- Token da API está válido
- Instance ID está correto
- Endpoints foram ajustados conforme documentação

## Contribuição

Sugestões e melhorias são bem-vindas! Abra uma issue ou pull request.

## Licença

MIT License

---

**Desenvolvido com Python e Supabase**
