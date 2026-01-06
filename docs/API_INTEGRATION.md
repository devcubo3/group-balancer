# Guia de Integração com API WhatsApp (UAZAPI)

Este documento explica como ajustar o código para funcionar com a API real do WhatsApp.

## Endpoints que Precisam ser Ajustados

Os seguintes métodos em `src/whatsapp_service.py` precisam ser ajustados conforme a documentação da UAZAPI:

### 1. Criar Grupo (`create_group`)

**Localização**: `src/whatsapp_service.py:58`

**Exemplo genérico atual**:
```python
endpoint = f"instances/{self.instance_id}/groups/create"
payload = {
    "name": group_name,
    "description": description
}
```

**Você precisa ajustar para**:
- Endpoint correto da UAZAPI
- Estrutura correta do payload
- Parsing da resposta (extrair ID do grupo)

**Exemplo de como deve ficar** (ajuste conforme doc):
```python
endpoint = "groups/create"  # Exemplo
payload = {
    "groupName": group_name,
    "groupDescription": description
}

# Parsing da resposta
response = self._make_request("POST", endpoint, data=payload)
if response:
    group_id = response.get("data", {}).get("groupId")
    return response
```

### 2. Obter Informações do Grupo (`get_group_info`)

**Localização**: `src/whatsapp_service.py:86`

**Você precisa ajustar**:
- Endpoint para buscar info do grupo
- Mapeamento dos campos da resposta (nome, contagem de membros, link)

**Exemplo**:
```python
endpoint = f"groups/{group_id}/info"

# Ajustar o parsing conforme estrutura real
return GroupInfoResponse(
    group_id=response["data"]["id"],
    name=response["data"]["subject"],
    member_count=len(response["data"]["participants"]),
    invite_link=response["data"]["inviteCode"]
)
```

### 3. Obter Link de Convite (`get_group_invite_link`)

**Localização**: `src/whatsapp_service.py:129`

**Você precisa ajustar**:
- Endpoint para obter/gerar link de convite
- Formato da resposta

### 4. Headers de Autenticação

**Localização**: `src/whatsapp_service.py:21`

Atualmente usando:
```python
self.headers = {
    "Authorization": f"Bearer {self.token}",
    "Content-Type": "application/json"
}
```

Verifique se a UAZAPI usa este formato ou outro (ex: `X-API-Key`, `apikey`, etc).

## Como Descobrir os Endpoints Corretos

### Opção 1: Você me fornece exemplos de chamadas Python

Se você já tem exemplos de código Python funcionando com a API, envie aqui e eu ajusto o código.

**Exemplo do que preciso**:
```python
# Exemplo de como você cria um grupo atualmente
import requests

response = requests.post(
    "https://api.uazapi.com/v1/groups/create",
    headers={"X-API-KEY": "seu_token"},
    json={
        "name": "Meu Grupo",
        "participants": []
    }
)

# Me mostre a estrutura da resposta
print(response.json())
```

### Opção 2: Documentação da API

Se você tiver acesso à documentação completa da UAZAPI (PDF, link alternativo, ou screenshots), posso ajustar precisamente.

### Opção 3: Teste Incremental

1. Configure o `.env` com suas credenciais
2. Execute o teste de conexão:
   ```bash
   python main.py test
   ```
3. Me envie os erros que aparecerem
4. Vou ajustar o código iterativamente

## Estrutura de Resposta Esperada

Para cada endpoint, precisamos saber:

### Criar Grupo
```json
{
  "success": true,
  "data": {
    "groupId": "120363123456789@g.us",
    "groupName": "Grupo 101",
    "inviteLink": "https://chat.whatsapp.com/XXXXXX"
  }
}
```

### Obter Info do Grupo
```json
{
  "success": true,
  "data": {
    "id": "120363123456789@g.us",
    "subject": "Grupo 101",
    "participants": [...],  // Array com membros
    "size": 850,  // ou participantsCount
    "inviteCode": "https://chat.whatsapp.com/XXXXXX"
  }
}
```

## Próximos Passos

1. **Você me fornece** exemplos de chamadas da API ou documentação
2. **Eu ajusto** os endpoints em `whatsapp_service.py`
3. **Testamos** com o comando `python main.py test`
4. **Refinamos** conforme necessário

## Checklist de Integração

- [ ] Endpoints corretos configurados
- [ ] Headers de autenticação ajustados
- [ ] Parsing de respostas implementado
- [ ] Teste de criação de grupo funcionando
- [ ] Teste de obtenção de info funcionando
- [ ] Teste de link de convite funcionando
- [ ] Rate limiting testado e configurado
- [ ] Erros da API sendo tratados corretamente

---

**Aguardando seus exemplos ou documentação para finalizar a integração!**
