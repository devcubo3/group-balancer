# Documentação Completa da API UAZAPI - Endpoints de Grupos

Documentação detalhada dos endpoints de grupos da UAZAPI obtida em: https://docs.uazapi.com/

## 📋 Índice

1. [Autenticação](#autenticação)
2. [Endpoint: Criar Grupo](#1-criar-grupo)
3. [Endpoint: Obter Informações do Grupo](#2-obter-informações-do-grupo)
4. [Endpoint: Listar Todos os Grupos](#3-listar-todos-os-grupos)
5. [Estrutura Completa dos Objetos](#estrutura-completa-dos-objetos)

---

## Autenticação

Todos os endpoints da UAZAPI requerem autenticação via header HTTP.

### Header Obrigatório

```
token: seu_token_da_instancia
```

**Importante:**
- Endpoints regulares requerem um header `token` com o token da instância
- Endpoints administrativos requerem um header `admintoken`

### URL Base

```
https://{subdomain}.uazapi.com
```

Onde `{subdomain}` é o subdomínio do seu servidor (ex: `free`, `premium`, etc.)

---

## 1. CRIAR GRUPO

### Informações Gerais

**Endpoint:** `/group/create`  
**Método:** `POST`  
**URL Completa:** `https://{subdomain}.uazapi.com/group/create`

### Descrição

Cria um novo grupo no WhatsApp com participantes iniciais.

### Headers

```
token: seu_token_da_instancia
Content-Type: application/json
```

### Campos do Request Body

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `name` | string | ✅ Sim | Nome do grupo |
| `participants` | array | ✅ Sim | Lista de números de telefone dos participantes iniciais (apenas dígitos, sem formatação) |

### Exemplo de Request JSON

```json
{
  "name": "Meu Novo Grupo",
  "participants": [
    "5521987905995",
    "5511912345678"
  ]
}
```

### Detalhes Importantes

- ✅ Requer autenticação via token da instância
- ✅ Os números devem ser fornecidos sem formatação (apenas dígitos)
- ✅ Mínimo de 1 participante além do criador

### Comportamento

- Retorna informações detalhadas do grupo criado
- Inclui lista de participantes adicionados com sucesso/falha

### Exemplo de Response JSON Completo (200 - Sucesso)

```json
{
  "JID": "120363153742561022@g.us",
  "OwnerJID": "5521987905995@s.whatsapp.net",
  "OwnerPN": "string",
  "Name": "Grupo de Suporte",
  "NameSetAt": "2024-01-15T10:30:00Z",
  "NameSetBy": "string",
  "NameSetByPN": "string",
  "Topic": "string",
  "TopicID": "string",
  "TopicSetAt": "2024-01-15T10:30:00Z",
  "TopicSetBy": "string",
  "TopicSetByPN": "string",
  "TopicDeleted": false,
  "IsLocked": true,
  "IsAnnounce": false,
  "AnnounceVersionID": "string",
  "IsEphemeral": false,
  "DisappearingTimer": 0,
  "IsIncognito": false,
  "IsParent": false,
  "IsJoinApprovalRequired": false,
  "LinkedParentJID": "string",
  "IsDefaultSubGroup": false,
  "DefaultMembershipApprovalMode": "string",
  "GroupCreated": "2024-01-15T10:30:00Z",
  "CreatorCountryCode": "string",
  "ParticipantVersionID": "string",
  "Participants": [
    {
      "JID": "5511912345678@s.whatsapp.net",
      "LID": "string",
      "IsAdmin": false,
      "IsSuperAdmin": false
    }
  ],
  "MemberAddMode": "admin_add",
  "AddressingMode": "pn",
  "OwnerCanSendMessage": false,
  "OwnerIsAdmin": false,
  "DefaultSubGroupId": "string",
  "invite_link": "https://chat.whatsapp.com/xxxxxxxxxxxxxxx",
  "request_participants": "string"
}
```

### Códigos de Resposta

| Código | Descrição |
|--------|-----------|
| 200 | Grupo criado com sucesso |
| 400 | Erro de payload inválido |
| 500 | Erro interno do servidor |

---

## 2. OBTER INFORMAÇÕES DO GRUPO

### Informações Gerais

**Endpoint:** `/group/info`  
**Método:** `POST`  
**URL Completa:** `https://{subdomain}.uazapi.com/group/info`

### Descrição

Recupera informações completas de um grupo do WhatsApp, incluindo:
- Detalhes do grupo
- Participantes
- Configurações
- Link de convite (opcional)

### Headers

```
token: seu_token_da_instancia
Content-Type: application/json
```

### Campos do Request Body

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `groupjid` | string | ✅ Sim | Identificador único do grupo (JID) no formato `120363153742561022@g.us` |
| `getInviteLink` | boolean | ❌ Não | Recuperar link de convite do grupo (padrão: false) |
| `getRequestsParticipants` | boolean | ❌ Não | Recuperar lista de solicitações pendentes de participação (padrão: false) |
| `force` | boolean | ❌ Não | Forçar atualização, ignorando cache (padrão: false) |

### Exemplo de Request JSON

```json
{
  "groupjid": "120363153742561022@g.us",
  "getInviteLink": true,
  "getRequestsParticipants": false,
  "force": false
}
```

### Como Passar o ID do Grupo

O ID do grupo (JID) é retornado no campo `JID` ao criar um grupo. Formato:
- Exemplo: `120363153742561022@g.us`
- Sempre termina com `@g.us` (indicando que é um grupo)

### Exemplo de Response JSON Completo (200 - Sucesso)

```json
{
  "JID": "120363153742561022@g.us",
  "OwnerJID": "5521987905995@s.whatsapp.net",
  "OwnerPN": "string",
  "Name": "Grupo de Suporte",
  "NameSetAt": "2024-01-15T10:30:00Z",
  "NameSetBy": "string",
  "NameSetByPN": "string",
  "Topic": "string",
  "TopicID": "string",
  "TopicSetAt": "2024-01-15T10:30:00Z",
  "TopicSetBy": "string",
  "TopicSetByPN": "string",
  "TopicDeleted": false,
  "IsLocked": true,
  "IsAnnounce": false,
  "AnnounceVersionID": "string",
  "IsEphemeral": false,
  "DisappearingTimer": 0,
  "IsIncognito": false,
  "IsParent": false,
  "IsJoinApprovalRequired": false,
  "LinkedParentJID": "string",
  "IsDefaultSubGroup": false,
  "DefaultMembershipApprovalMode": "string",
  "GroupCreated": "2024-01-15T10:30:00Z",
  "CreatorCountryCode": "string",
  "ParticipantVersionID": "string",
  "Participants": [
    {
      "JID": "5511912345678@s.whatsapp.net",
      "LID": "string",
      "IsAdmin": false,
      "IsSuperAdmin": false
    }
  ],
  "MemberAddMode": "admin_add",
  "AddressingMode": "pn",
  "OwnerCanSendMessage": false,
  "OwnerIsAdmin": false,
  "DefaultSubGroupId": "string",
  "invite_link": "https://chat.whatsapp.com/xxxxxxxxxxxxxxx",
  "request_participants": "string"
}
```

### Códigos de Resposta

| Código | Descrição |
|--------|-----------|
| 200 | Informações do grupo obtidas com sucesso |
| 400 | Código de convite inválido ou mal formatado |
| 404 | Grupo não encontrado ou link de convite expirado |
| 500 | Erro interno do servidor |

---

## 3. LISTAR TODOS OS GRUPOS

### Informações Gerais

**Endpoint:** `/group/list`  
**Método:** `GET`  
**URL Completa:** `https://{subdomain}.uazapi.com/group/list`

### Descrição

Retorna uma lista com todos os grupos disponíveis para a instância atual do WhatsApp.

### Headers

```
token: seu_token_da_instancia
```

### Query Parameters (Opcionais)

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `force` | boolean | ❌ Não | Se `true`, força a atualização do cache de grupos (padrão: `false`) |
| `noparticipants` | boolean | ❌ Não | Se `true`, retorna grupos sem incluir participantes (padrão: `false`) |

### Comportamento dos Parâmetros

**force:**
- `false` (padrão): Usa informações em cache
- `true`: Busca dados atualizados diretamente do WhatsApp

**noparticipants:**
- `false` (padrão): Retorna grupos com lista completa de participantes
- `true`: Retorna grupos sem incluir os participantes (otimiza a resposta)

### Exemplo de Request

```bash
GET https://free.uazapi.com/group/list?force=false&noparticipants=false
```

### Exemplo de Response JSON Completo (200 - Sucesso)

```json
{
  "groups": [
    {
      "JID": "120363153742561022@g.us",
      "OwnerJID": "5521987905995@s.whatsapp.net",
      "OwnerPN": "string",
      "Name": "Grupo de Suporte",
      "NameSetAt": "2024-01-15T10:30:00Z",
      "NameSetBy": "string",
      "NameSetByPN": "string",
      "Topic": "string",
      "TopicID": "string",
      "TopicSetAt": "2024-01-15T10:30:00Z",
      "TopicSetBy": "string",
      "TopicSetByPN": "string",
      "TopicDeleted": false,
      "IsLocked": true,
      "IsAnnounce": false,
      "AnnounceVersionID": "string",
      "IsEphemeral": false,
      "DisappearingTimer": 0,
      "IsIncognito": false,
      "IsParent": false,
      "IsJoinApprovalRequired": false,
      "LinkedParentJID": "string",
      "IsDefaultSubGroup": false,
      "DefaultMembershipApprovalMode": "string",
      "GroupCreated": "2024-01-15T10:30:00Z",
      "CreatorCountryCode": "string",
      "ParticipantVersionID": "string",
      "Participants": [
        {
          "JID": "5511912345678@s.whatsapp.net",
          "LID": "string",
          "IsAdmin": false,
          "IsSuperAdmin": false
        }
      ],
      "MemberAddMode": "admin_add",
      "AddressingMode": "pn",
      "OwnerCanSendMessage": false,
      "OwnerIsAdmin": false,
      "DefaultSubGroupId": "string",
      "invite_link": "https://chat.whatsapp.com/xxxxxxxxxxxxxxx",
      "request_participants": "string"
    }
  ]
}
```

### Códigos de Resposta

| Código | Descrição |
|--------|-----------|
| 200 | Lista de grupos recuperada com sucesso |
| 500 | Erro interno do servidor ao recuperar grupos |

---

## Estrutura Completa dos Objetos

### Objeto Group (Grupo)

Todos os campos retornados pela API para um grupo:

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `JID` | string | ID único do grupo (formato: `123456789@g.us`) |
| `OwnerJID` | string | JID do proprietário/criador do grupo |
| `OwnerPN` | string | Número de telefone do proprietário |
| `Name` | string | Nome do grupo |
| `NameSetAt` | string (ISO 8601) | Data/hora em que o nome foi definido |
| `NameSetBy` | string | JID de quem definiu o nome |
| `NameSetByPN` | string | Número de telefone de quem definiu o nome |
| `Topic` | string | Descrição/tópico do grupo |
| `TopicID` | string | ID do tópico |
| `TopicSetAt` | string (ISO 8601) | Data/hora em que o tópico foi definido |
| `TopicSetBy` | string | JID de quem definiu o tópico |
| `TopicSetByPN` | string | Número de telefone de quem definiu o tópico |
| `TopicDeleted` | boolean | Se o tópico foi deletado |
| `IsLocked` | boolean | Se o grupo está bloqueado |
| `IsAnnounce` | boolean | Se apenas admins podem enviar mensagens |
| `AnnounceVersionID` | string | Versão da configuração de anúncios |
| `IsEphemeral` | boolean | Se as mensagens são temporárias |
| `DisappearingTimer` | integer | Tempo (segundos) para mensagens desaparecerem |
| `IsIncognito` | boolean | Se o grupo é incógnito |
| `IsParent` | boolean | Se é um grupo pai (comunidade) |
| `IsJoinApprovalRequired` | boolean | Se requer aprovação para entrar |
| `LinkedParentJID` | string | JID do grupo pai (se for subgrupo) |
| `IsDefaultSubGroup` | boolean | Se é um subgrupo padrão |
| `DefaultMembershipApprovalMode` | string | Modo de aprovação padrão de membros |
| `GroupCreated` | string (ISO 8601) | Data/hora de criação do grupo |
| `CreatorCountryCode` | string | Código do país do criador |
| `ParticipantVersionID` | string | Versão da lista de participantes |
| `Participants` | array | Lista de participantes do grupo |
| `MemberAddMode` | string | Modo de adição de membros (ex: `admin_add`) |
| `AddressingMode` | string | Modo de endereçamento (ex: `pn`) |
| `OwnerCanSendMessage` | boolean | Se o proprietário pode enviar mensagens |
| `OwnerIsAdmin` | boolean | Se o proprietário é admin |
| `DefaultSubGroupId` | string | ID do subgrupo padrão |
| `invite_link` | string | Link de convite do grupo |
| `request_participants` | string | Participantes solicitando entrada |

### Objeto Participant (Participante)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `JID` | string | JID do participante (formato: `5511999999999@s.whatsapp.net`) |
| `LID` | string | ID local do participante |
| `IsAdmin` | boolean | Se o participante é administrador |
| `IsSuperAdmin` | boolean | Se o participante é super administrador |

---

## Campos Importantes para o Balanceador

Para o sistema de balanceamento de grupos, os campos mais relevantes são:

### Ao Criar/Listar Grupos:
- ✅ **`JID`** - ID único do grupo (necessário para todas as operações)
- ✅ **`Name`** - Nome do grupo
- ✅ **`Participants`** - Lista de participantes (para contar membros)
- ✅ **`invite_link`** - Link de convite do grupo
- ✅ **`GroupCreated`** - Data de criação

### Para Contar Membros:
```javascript
const memberCount = group.Participants?.length || 0;
```

### Para Identificar Grupos Cheios:
```javascript
const MAX_MEMBERS = 1024; // Limite do WhatsApp
const isFull = group.Participants?.length >= MAX_MEMBERS;
```

---

## Exemplo de Integração Completa

### 1. Criar um Grupo

```javascript
const response = await fetch('https://free.uazapi.com/group/create', {
  method: 'POST',
  headers: {
    'token': 'seu_token_aqui',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: 'Grupo Automático 1',
    participants: ['5511999999999']
  })
});

const newGroup = await response.json();
console.log('Grupo criado:', newGroup.JID);
console.log('Link:', newGroup.invite_link);
```

### 2. Listar Todos os Grupos

```javascript
const response = await fetch('https://free.uazapi.com/group/list?force=true', {
  method: 'GET',
  headers: {
    'token': 'seu_token_aqui'
  }
});

const data = await response.json();
console.log('Total de grupos:', data.groups.length);

// Filtrar grupos com menos de 1024 membros
const availableGroups = data.groups.filter(g => 
  (g.Participants?.length || 0) < 1024
);
```

### 3. Obter Informações de um Grupo Específico

```javascript
const response = await fetch('https://free.uazapi.com/group/info', {
  method: 'POST',
  headers: {
    'token': 'seu_token_aqui',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    groupjid: '120363153742561022@g.us',
    getInviteLink: true,
    force: true
  })
});

const groupInfo = await response.json();
console.log('Membros:', groupInfo.Participants.length);
console.log('Link:', groupInfo.invite_link);
```

---

## ⚠️ Observações Importantes

1. **WhatsApp Business Recomendado**: É ALTAMENTE RECOMENDADO usar contas do WhatsApp Business para integração com a API

2. **Formato de Números**: 
   - Sempre usar apenas dígitos
   - Incluir código do país
   - Exemplo: `5521987905995`

3. **Limite de Membros**:
   - Máximo de 1024 participantes por grupo no WhatsApp

4. **Rate Limiting**:
   - A API possui limites de uso
   - Erro 429 quando o limite é atingido

5. **Cache**:
   - Use `force=true` para garantir dados atualizados
   - Use `noparticipants=true` para otimizar quando não precisa da lista de participantes

---

## 🔗 Links Úteis

- Documentação Oficial: https://docs.uazapi.com/
- Servidor Base: https://{subdomain}.uazapi.com

---

**Última Atualização:** 05/01/2026  
**Versão da API:** v2.0
