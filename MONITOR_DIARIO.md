# Monitor Diário de Grupos

## 📋 Visão Geral

O sistema agora possui **2 monitores independentes** que trabalham em conjunto:

### 1️⃣ Monitor Principal (`main.py`)
- **Frequência**: Contínuo (verifica a cada 60 segundos)
- **Foco**: Apenas o grupo MAIS NOVO
- **Objetivo**: Detectar quando o grupo mais novo atinge 950 membros e criar um novo grupo automaticamente
- **Como executar**: `python main.py`

### 2️⃣ Monitor Diário (`daily_monitor.py`)
- **Frequência**: Uma vez por dia (execução manual ou agendada)
- **Foco**: TODOS os grupos ativos do sistema
- **Objetivo**: Manter a contagem de membros atualizada em todos os grupos, não apenas o mais novo
- **Como executar**: `python daily_monitor.py`

---

## 🎯 Por que preciso de 2 monitores?

### Problema que o Monitor Diário resolve:

Imagine o seguinte cenário:

```
📊 Sistema com 1000 grupos:

Grupo #001: 400 membros (tinha 900, mas saíram pessoas)
Grupo #002: 450 membros (tinha 850, mas saíram pessoas)
Grupo #003: 380 membros (tinha 920, mas saíram pessoas)
...
Grupo #999: 720 membros (tinha 900, mas saíram pessoas)
Grupo #1000: 950 membros (NOVO - monitorado pelo main.py)
```

**Problema**: O monitor principal (`main.py`) só vê o grupo #1000. Ele vai criar o grupo #1001 quando o #1000 chegar em 950 membros.

**MAS**: Os grupos #001, #002, #003... #999 que tinham muita gente e agora têm vagas NÃO são monitorados!

**Solução**: O monitor diário atualiza a contagem de TODOS os grupos, permitindo:
- Saber quais grupos têm vagas disponíveis
- Fazer balanceamento global (distribuir novos membros em grupos antigos com vagas)
- Não deixar grupos "para trás"

---

## ⚙️ Configurações

As configurações estão no arquivo `.env`:

```env
# Delay entre chamadas de API (em segundos)
# Usado pelo monitor diário para evitar rate limit
API_CALL_DELAY=2

# Timeout para chamadas de API (em segundos)
API_TIMEOUT=30

# Intervalo do monitor principal (em segundos)
MONITOR_CHECK_INTERVAL=60

# Intervalo da sincronização completa (em horas)
# Nota: O monitor principal faz uma sync a cada 12h
DAILY_SYNC_INTERVAL=24
```

---

## 🚀 Como Usar

### Execução Manual (Teste)

```bash
# Monitor principal (contínuo)
python main.py

# Monitor diário (execução única)
python daily_monitor.py
```

### Agendar Execução Diária

#### Windows (Task Scheduler)

1. Abrir "Agendador de Tarefas"
2. Criar Nova Tarefa
3. Configurar:
   - **Nome**: Monitor Diário de Grupos WhatsApp
   - **Gatilho**: Diariamente às 03:00
   - **Ação**: Iniciar programa
     - Programa: `python`
     - Argumentos: `daily_monitor.py`
     - Diretório: `C:\Users\davin\OneDrive\Projetos\group-balancer`

#### Linux (Cron)

```bash
# Editar crontab
crontab -e

# Adicionar linha (executa todo dia às 3h da manhã)
0 3 * * * cd /caminho/para/group-balancer && python daily_monitor.py >> logs/daily_monitor.log 2>&1
```

#### Docker/Servidor (Usando schedule no código)

Se preferir rodar tudo em um único processo, pode adicionar o agendamento no `main.py`:

```python
# Em monitor.py, método run_continuous():

# Agenda sincronização a cada 12 horas
schedule.every(settings.daily_sync_interval).hours.do(self.daily_sync)

# NOVO: Agenda monitoramento diário completo às 3h da manhã
schedule.every().day.at("03:00").do(self.daily_full_group_check)
```

---

## 📊 O que o Monitor Diário faz?

```
1. Busca TODOS os grupos ativos do Supabase
   └─> SELECT * FROM controle_grupos WHERE status = 'ativo'

2. Para cada grupo (um por vez):
   ├─> Consulta API do WhatsApp para pegar contagem atual
   ├─> Compara com a contagem no banco
   ├─> Se mudou: Atualiza no banco e salva log
   ├─> Se não mudou: Marca como "sem alteração"
   └─> Aguarda 2 segundos (API_CALL_DELAY) antes do próximo
       (evita rate limit)

3. Salva logs detalhados:
   ├─> Log individual de cada grupo atualizado
   └─> Log geral com resumo (total, atualizados, falhas)
```

---

## 📝 Logs Salvos

O monitor diário salva 2 tipos de logs na tabela `monitor_logs`:

### 1. Log Individual (`monitor_type = 'daily_individual'`)
```json
{
  "monitor_type": "daily_individual",
  "group_id_api": "120363123456789@g.us",
  "group_name": "Dona Promo #001",
  "member_count": 450,
  "previous_count": 400,
  "count_difference": 50,
  "status_message": "Grupo atualizado: 400 → 450",
  "has_error": false
}
```

### 2. Log Geral (`monitor_type = 'daily_full_check'`)
```json
{
  "monitor_type": "daily_full_check",
  "status_message": "Monitoramento diário: 1000 grupos | Atualizados: 234 | Sem alteração: 750 | Falhas: 16 | Total membros: 678500",
  "has_error": false
}
```

---

## 🔍 Monitorando os Logs

### Ver último monitoramento diário:
```sql
SELECT * FROM monitor_logs 
WHERE monitor_type = 'daily_full_check' 
ORDER BY created_at DESC 
LIMIT 1;
```

### Ver grupos que mudaram hoje:
```sql
SELECT * FROM monitor_logs 
WHERE monitor_type = 'daily_individual' 
  AND count_difference != 0
  AND created_at > NOW() - INTERVAL '24 hours'
ORDER BY ABS(count_difference) DESC;
```

### Ver grupos com problemas:
```sql
SELECT * FROM monitor_logs 
WHERE monitor_type = 'daily_individual' 
  AND has_error = true
  AND created_at > NOW() - INTERVAL '24 hours';
```

---

## ✅ Checklist de Implementação

- [x] Criar função `daily_full_group_check()` no `GroupMonitor`
- [x] Criar script `daily_monitor.py` para execução independente
- [x] Adicionar configurações no `.env`
- [x] Documentar funcionamento
- [ ] Testar execução manual
- [ ] Agendar execução diária (Task Scheduler/Cron)
- [ ] Monitorar logs no Supabase

---

## 🆚 Diferenças: Monitor Principal vs Monitor Diário

| Característica | Monitor Principal (`main.py`) | Monitor Diário (`daily_monitor.py`) |
|---|---|---|
| **Frequência** | Contínuo (60s) | 1x por dia |
| **Grupos monitorados** | Apenas o mais novo | TODOS os grupos |
| **Objetivo** | Criar novos grupos | Atualizar contagens |
| **Execução** | Loop infinito | Execução única |
| **Agendamento** | Sempre rodando | Agendado (cron/scheduler) |
| **Logs salvos** | `newest_group`, `full_sync` | `daily_individual`, `daily_full_check` |

---

## 💡 Próximos Passos

Depois de implementar o monitor diário, você pode:

1. **Criar lógica de balanceamento global**:
   - Ao invés de sempre redirecionar para o grupo mais novo
   - Buscar grupos antigos com vagas disponíveis
   - Distribuir novos membros de forma equilibrada

2. **Dashboard de monitoramento**:
   - Visualizar quantos grupos têm vagas
   - Ver tendências de crescimento/redução
   - Alertas para grupos com problemas

3. **Otimização de capacidade**:
   - Identificar grupos "vazios" (< 100 membros)
   - Sugerir consolidação de grupos
   - Previsão de quando criar novos grupos

---

**Autor**: Sistema de Balanceamento de Grupos WhatsApp  
**Data**: 2026-01-06  
**Versão**: 1.0
