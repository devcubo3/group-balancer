# 🎉 Novas Funcionalidades - Group Balancer

## 📝 Atualização - Janeiro 2026

### Resumo das Melhorias

Implementamos 3 novas funcionalidades importantes para melhorar a gestão dos grupos do WhatsApp:

---

## ✨ Funcionalidades Implementadas

### 1. 📝 Descrição Automática do Grupo

Agora todos os grupos criados automaticamente recebem uma descrição personalizada que você configura no arquivo `.env`.

**Variável de Ambiente:**
```env
GROUP_DESCRIPTION=Bem-vindo ao grupo! Este é um espaço exclusivo para promoções e ofertas incríveis.
```

**Endpoint UAZAPI Utilizado:**
- `POST /group/updatedescription`

**Método Implementado:**
```python
whatsapp_service.update_group_description(group_id, description)
```

---

### 2. 🖼️ Imagem Automática do Grupo

Todos os grupos criados agora recebem automaticamente a imagem configurada no `.env`.

**Variável de Ambiente:**
```env
GROUP_IMAGE_URL=https://exemplo.com/imagem-do-grupo.jpg
```

**Endpoint UAZAPI Utilizado:**
- `POST /group/updatepicture`

**Método Implementado:**
```python
whatsapp_service.update_group_picture(group_id, image_url)
```

**⚠️ Importante:** A URL deve ser acessível publicamente e apontar para uma imagem válida (JPG, PNG, etc).

---

### 3. 🔒 Permissões de Mensagens (Somente Admins)

Os grupos são automaticamente configurados para que **apenas administradores** possam enviar mensagens. Isso evita spam e mantém o controle total sobre o conteúdo.

**Endpoint UAZAPI Utilizado:**
- `POST /group/updateAnnounce`

**Método Implementado:**
```python
whatsapp_service.set_group_messaging_permissions(group_id, only_admins=True)
```

**Comportamento:**
- `only_admins=True`: Apenas admins podem enviar mensagens (padrão)
- `only_admins=False`: Todos os participantes podem enviar mensagens

---

## 🔧 Configuração

### 1. Atualize seu arquivo `.env`

Adicione ou atualize as seguintes variáveis:

```env
# ==============================================
# WHATSAPP API CONFIGURATION (UAZAPI)
# ==============================================
WHATSAPP_API_URL=https://free.uazapi.com
WHATSAPP_API_TOKEN=d2ff2337-c38c-46fa-9e1b-6d3689e23f99
WHATSAPP_ADMIN_NUMBER=553391269004

# Configurações de Grupo
GROUP_DESCRIPTION=Bem-vindo ao grupo! Este é um espaço exclusivo para promoções e ofertas incríveis.
GROUP_IMAGE_URL=https://exemplo.com/imagem-do-grupo.jpg
```

### 2. Credenciais Atualizadas

As credenciais da API já foram atualizadas para:

- **Server URL:** `https://free.uazapi.com`
- **Instance Token:** `d2ff2337-c38c-46fa-9e1b-6d3689e23f99`
- **Número Conectado:** `553391269004`
- **Status:** ✅ Connected

---

## 📚 Como Usar

### Criação Automática de Grupos

Quando um novo grupo é criado (seja automaticamente pelo monitor ou manualmente), o sistema agora:

1. ✅ Cria o grupo
2. ⏳ Aguarda rate limit (2 segundos)
3. ✅ Aplica a descrição configurada
4. ⏳ Aguarda rate limit (2 segundos)
5. ✅ Aplica a imagem configurada
6. ⏳ Aguarda rate limit (2 segundos)
7. ✅ Configura permissões (somente admins)

### Exemplo de Código

```python
from src.load_balancer import LoadBalancer

lb = LoadBalancer()

# Cria um novo grupo com todas as configurações automáticas
grupo = lb.create_new_group(
    group_number=1,
    group_name="Dona Promo #001"
)

# O grupo já terá:
# - Descrição da env GROUP_DESCRIPTION
# - Imagem da env GROUP_IMAGE_URL
# - Permissões configuradas (somente admins)
```

### Atualizar Grupos Existentes

Se você já tem grupos criados e quer aplicar as novas configurações:

```python
from src.whatsapp_service import WhatsAppService

whatsapp = WhatsAppService()

# Atualizar descrição
whatsapp.update_group_description(
    group_id="120363123456789@g.us",
    description="Nova descrição"
)

# Atualizar imagem
whatsapp.update_group_picture(
    group_id="120363123456789@g.us",
    image_url="https://exemplo.com/nova-imagem.jpg"
)

# Configurar permissões
whatsapp.set_group_messaging_permissions(
    group_id="120363123456789@g.us",
    only_admins=True  # ou False para liberar para todos
)
```

---

## 🔍 Endpoints da API UAZAPI

Todos os endpoints implementados foram baseados na documentação oficial:

**Documentação:** https://docs.uazapi.com/tag/Grupos%20e%20Comunidades

### Endpoints Utilizados:

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/group/create` | Criar novo grupo |
| POST | `/group/updatedescription` | Atualizar descrição do grupo |
| POST | `/group/updatepicture` | Atualizar imagem do grupo |
| POST | `/group/updateAnnounce` | Configurar permissões de mensagens |

---

## 📊 Logs e Monitoramento

Todas as chamadas da API são registradas no banco de dados (tabela `api_call_logs`) com:

- ✅ Endpoint chamado
- ✅ Payload enviado
- ✅ Resposta recebida
- ✅ Status code
- ✅ Tempo de execução
- ✅ Success/Error

Você pode consultar os logs com:

```bash
python print_sql_api_logs.py
```

---

## ⚙️ Arquivos Modificados

### Atualizados:
1. `src/config.py` - Novas variáveis de ambiente
2. `src/whatsapp_service.py` - Novos métodos da API
3. `src/load_balancer.py` - Criação de grupos com descrição e imagem
4. `.env.example` - Exemplo com novas variáveis

### Novos Métodos:
- `update_group_description(group_id, description)` 
- `update_group_picture(group_id, image_url)`
- `set_group_messaging_permissions(group_id, only_admins)`

---

## ✅ Checklist de Configuração

- [ ] Atualizar arquivo `.env` com `GROUP_DESCRIPTION`
- [ ] Atualizar arquivo `.env` com `GROUP_IMAGE_URL`
- [ ] Verificar se `WHATSAPP_API_TOKEN` está correto
- [ ] Verificar se `WHATSAPP_ADMIN_NUMBER` está correto
- [ ] Testar criação de novo grupo
- [ ] Verificar se descrição foi aplicada
- [ ] Verificar se imagem foi aplicada
- [ ] Verificar se permissões estão configuradas (somente admins)

---

## 🎯 Próximos Passos

Algumas sugestões para expandir ainda mais:

1. Criar comando para atualizar grupos existentes em lote
2. Adicionar opção de escolher entre diferentes templates de descrição
3. Permitir múltiplas imagens e rotacioná-las
4. Criar dashboard para gerenciar configurações visuais dos grupos

---

## 📞 Suporte

Em caso de dúvidas ou problemas:

1. Verifique os logs: `python print_sql_api_logs.py`
2. Consulte a documentação da API: https://docs.uazapi.com
3. Verifique se a instância está conectada no painel da UAZAPI

---

**Última Atualização:** Janeiro 2026
**Versão:** 2.0
