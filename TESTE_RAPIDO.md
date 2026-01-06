# 🧪 Guia de Teste Rápido - Monitoramento em Tempo Real

Este guia te ajuda a testar o sistema completo de monitoramento dos grupos.

## 📋 Passo a Passo

### 1️⃣ Criar o Primeiro Grupo

```bash
python create_first_group.py
```

Isso vai criar o grupo inicial (Dona Promo #001) no WhatsApp e registrar no Supabase.

**Resultado esperado:**
```
✅ Grupo criado com sucesso!
   Nome: Dona Promo #001
   ID: 120363...@g.us
   Link: https://chat.whatsapp.com/...
```

---

### 2️⃣ Ativar o Monitor Principal (Grupo Mais Novo)

Abra um **Terminal 1** e execute:

```bash
python main.py
```

**O que acontece:**
- Monitora o grupo mais novo a cada 60 segundos
- Quando atingir 950 membros → cria novo grupo automaticamente
- Continua rodando até você pressionar Ctrl+C

**Saída esperada:**
```
🚀 MONITOR DE GRUPOS INICIADO
   Intervalo de verificação: 60s
   Threshold para criar novo grupo: 950 membros
============================================================
🔍 VERIFICAÇÃO AUTOMÁTICA - 2026-01-06 15:30:45
============================================================
📊 Verificando grupo: Dona Promo #001
✓ Sistema OK - Dona Promo #001 (1/950 membros)
```

---

### 3️⃣ Adicionar Membros (Criar mais 2 grupos)

**Opção A: Manualmente via WhatsApp**
- Adicione pessoas no grupo #001
- Quando atingir 950 membros → grupo #002 será criado automaticamente
- Continue adicionando no #002
- Quando atingir 950 membros → grupo #003 será criado

**Opção B: Simular via código (para testes)**

Você pode atualizar manualmente a contagem no Supabase:

```sql
-- No Supabase SQL Editor
UPDATE controle_grupos 
SET membros_atuais = 950 
WHERE subject = 'Dona Promo #001';
```

Aguarde 60 segundos e o monitor vai detectar e criar o grupo #002.

Repita para criar o #003.

---

### 4️⃣ Ativar o Monitor Diário (Modo Teste - 3 minutos)

Depois de ter **3 grupos criados**, abra um **Terminal 2** e execute:

```bash
python test_daily_monitor.py
```

**Ou com intervalo customizado:**

```bash
# 1 minuto (teste muito rápido)
python test_daily_monitor.py --interval 1

# 5 minutos
python test_daily_monitor.py --interval 5
```

**O que acontece:**
- Busca TODOS os grupos ativos (os 3 grupos)
- Sincroniza a contagem de cada um com a API
- Aguarda 3 minutos
- Repete o processo
- Continua em loop até Ctrl+C

**Saída esperada:**
```
🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪
🧪 MONITOR DIÁRIO EM LOOP - MODO TESTE
🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪🧪
⏱️  Intervalo: 3 minutos (180s)
🎯 Monitora: TODOS os grupos ativos
🔄 Modo: Loop contínuo (Ctrl+C para parar)

================================================================================
🔄 EXECUÇÃO #1
📅 2026-01-06 15:35:00
================================================================================

🌍 MONITORAMENTO DIÁRIO COMPLETO - 2026-01-06 15:35:00
============================================================
📊 Total de grupos a verificar: 3
⏱️ Delay entre chamadas: 2s
------------------------------------------------------------

[1/3] 🔍 Verificando: Dona Promo #001
   ID API: 120363123456789@g.us
   Membros atuais (banco): 950
   ✅ ATUALIZADO: 950 → 952 (+2)

⏳ Aguardando 2s...

[2/3] 🔍 Verificando: Dona Promo #002
   ID API: 120363987654321@g.us
   Membros atuais (banco): 850
   ✓ Sem alteração (850 membros)

⏳ Aguardando 2s...

[3/3] 🔍 Verificando: Dona Promo #003
   ID API: 120363555555555@g.us
   Membros atuais (banco): 100
   ✅ ATUALIZADO: 100 → 105 (+5)

============================================================
📊 RESUMO DO MONITORAMENTO DIÁRIO
============================================================
   Total de grupos verificados: 3
   ✅ Atualizados: 2
   ✓ Sem alteração: 1
   ✗ Falhas: 0
   👥 Total de membros: 1907
============================================================

--------------------------------------------------------------------------------
✅ Execução #1 concluída!
⏳ Próxima execução em 3 minutos
🕐 Próximo horário: 15:38:00
⏹️  Pressione Ctrl+C para parar
--------------------------------------------------------------------------------

⏳ Aguardando... 3min 0s restantes
⏳ Aguardando... 2min 0s restantes
⏳ Aguardando... 1min 0s restantes
⏳ Aguardando... 30s restantes
⏳ Aguardando... 10s restantes
```

---

## 🎬 Estrutura Final dos Terminais

**Terminal 1: Monitor Principal**
```
python main.py
```
- Fica rodando continuamente
- Monitora apenas o grupo MAIS NOVO
- Cria novos grupos quando necessário

**Terminal 2: Monitor Diário (Teste)**
```
python test_daily_monitor.py
```
- Fica rodando em loop
- A cada 3 minutos verifica TODOS os grupos
- Mostra atualizações em tempo real

---

## 📊 Acompanhamento em Tempo Real

### Ver Logs no Supabase

Acesse o Supabase e execute:

```sql
-- Últimas 10 verificações do monitor diário
SELECT 
  created_at,
  monitor_type,
  group_name,
  member_count,
  previous_count,
  count_difference,
  status_message
FROM monitor_logs 
WHERE monitor_type IN ('daily_individual', 'daily_full_check')
ORDER BY created_at DESC 
LIMIT 10;
```

### Ver Grupos Atuais

```sql
-- Todos os grupos ativos
SELECT 
  subject as nome,
  membros_atuais,
  status,
  created_at,
  link_convite
FROM controle_grupos 
WHERE status = 'ativo'
ORDER BY created_at;
```

### Ver Mudanças Recentes

```sql
-- Grupos que tiveram mudança de membros nas últimas 10 min
SELECT 
  group_name,
  previous_count,
  member_count,
  count_difference,
  created_at
FROM monitor_logs 
WHERE monitor_type = 'daily_individual'
  AND count_difference != 0
  AND created_at > NOW() - INTERVAL '10 minutes'
ORDER BY created_at DESC;
```

---

## ⏹️ Para Parar os Monitores

Pressione **Ctrl+C** em cada terminal:

**Terminal 1:**
```
^C
⚠ Interrupção pelo usuário (Ctrl+C)
🛑 Encerrando monitor...
```

**Terminal 2:**
```
^C
⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️
⚠️  INTERRUPÇÃO PELO USUÁRIO (Ctrl+C)
⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️
📊 Total de execuções: 5
🛑 Encerrando monitor de testes...
```

---

## 🎯 Cenários de Teste

### Cenário 1: Criar Grupos Automaticamente
1. Criar grupo #001
2. Simular 950 membros no #001 (SQL ou adicionar pessoas)
3. Aguardar 60s → grupo #002 criado
4. Simular 950 membros no #002
5. Aguardar 60s → grupo #003 criado

### Cenário 2: Membros Saindo dos Grupos
1. Ter 3 grupos com muitos membros
2. Simular saída de membros (reduzir contagem no Supabase)
3. Monitor diário vai detectar e atualizar

### Cenário 3: Monitoramento Contínuo
1. Deixar ambos monitores rodando
2. Adicionar/remover pessoas dos grupos via WhatsApp
3. Acompanhar logs em tempo real
4. Ver atualizações no Supabase

---

## 🐛 Troubleshooting

### Monitor não cria grupo novo
- Verifique se o grupo tem >= 950 membros
- Verifique se o monitor principal está rodando
- Aguarde 60 segundos (intervalo de verificação)

### Monitor diário não atualiza contagens
- Verifique conexão com a API do WhatsApp
- Veja logs de erro no terminal
- Verifique se o API_CALL_DELAY está configurado (2s)

### Rate Limit da API
- Aumente API_CALL_DELAY no .env (de 2s para 5s)
- Use intervalos maiores no monitor de teste (5-10 min)

---

## 📝 Arquivos de Log

Os logs são salvos em:
- **Console**: Saída em tempo real
- **Arquivo**: `logs/monitor.log`
- **Banco**: Tabela `monitor_logs` no Supabase

---

## ✅ Checklist de Teste

- [ ] Grupo inicial criado com sucesso
- [ ] Monitor principal rodando no Terminal 1
- [ ] Conseguiu criar grupo #002 automaticamente
- [ ] Conseguiu criar grupo #003 automaticamente
- [ ] Monitor diário rodando no Terminal 2
- [ ] Monitor diário verificou todos os 3 grupos
- [ ] Logs sendo salvos no Supabase
- [ ] Contagens sendo atualizadas corretamente

---

**Boa sorte com os testes! 🚀**
