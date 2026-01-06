# Início Rápido

## Configuração em 5 Passos

### 1. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 2. Configurar Ambiente

Copie `.env.example` para `.env` e preencha:

```env
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=sua_chave_service_role

WHATSAPP_API_URL=https://api.uazapi.com
WHATSAPP_API_TOKEN=seu_token
WHATSAPP_INSTANCE_ID=sua_instancia
```

### 3. Criar Tabela no Supabase

Execute o SQL em `docs/SUPABASE_SCHEMA.sql` no SQL Editor do Supabase.

### 4. Ajustar API do WhatsApp

Leia `docs/API_INTEGRATION.md` e ajuste os endpoints em [src/whatsapp_service.py](src/whatsapp_service.py) conforme a documentação da UAZAPI.

### 5. Testar

```bash
# Testar conexões
python main.py test

# Criar primeiro grupo manualmente
python main.py create-group --group-number 1

# Iniciar monitor
python main.py monitor
```

## Estrutura de Arquivos Criados

```
group-balancer/
├── src/
│   ├── config.py              ⚙️ Configurações
│   ├── models.py              📦 Modelos de dados
│   ├── supabase_client.py     🗄️ Cliente Supabase
│   ├── whatsapp_service.py    📱 API WhatsApp (AJUSTAR AQUI!)
│   ├── load_balancer.py       ⚖️ Algoritmo principal
│   └── monitor.py             👁️ Monitor contínuo
├── docs/
│   ├── SUPABASE_SCHEMA.sql    📝 Schema do banco
│   └── API_INTEGRATION.md     📖 Guia de integração API
├── main.py                    🚀 Script principal
├── requirements.txt
├── .env.example
└── README.md
```

## Próximos Passos

1. **Você precisa me fornecer**: Exemplos de chamadas da API WhatsApp em Python
2. **Eu ajusto**: Os endpoints em `whatsapp_service.py`
3. **Você testa**: `python main.py test`
4. **Deploy**: Colocar para rodar em servidor

## Comandos Úteis

```bash
# Executar monitor (loop infinito)
python main.py monitor

# Sincronizar todos os grupos manualmente
python main.py sync

# Criar novo grupo
python main.py create-group

# Buscar melhor grupo para lead
python main.py get-best-group

# Testar conexões
python main.py test
```

## Troubleshooting

### Problema: ModuleNotFoundError

```bash
pip install -r requirements.txt
```

### Problema: Erro de conexão Supabase

Verifique URL e Key no `.env`

### Problema: API WhatsApp não responde

Leia `docs/API_INTEGRATION.md` e ajuste os endpoints

---

**Estou pronto para ajustar os endpoints da API assim que você fornecer os exemplos!**
