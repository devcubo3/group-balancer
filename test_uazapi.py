#!/usr/bin/env python3
"""
Script de teste manual da API UAZAPI.
Use este script para descobrir os endpoints corretos e testar a API.
"""
import httpx
import json
from dotenv import load_dotenv
import os

# Carrega variáveis de ambiente
load_dotenv()

API_URL = os.getenv("WHATSAPP_API_URL")
API_TOKEN = os.getenv("WHATSAPP_API_TOKEN")
ADMIN_NUMBER = os.getenv("WHATSAPP_ADMIN_NUMBER")

print(f"🔧 Teste da API UAZAPI")
print(f"URL: {API_URL}")
print(f"Token: {API_TOKEN[:20]}...")
print(f"Admin Number: {ADMIN_NUMBER}")
print("=" * 60)

# Headers comuns para testar
headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

# Teste 1: Listar grupos existentes
print("\n📋 Teste 1: Listando grupos existentes...")
print("Testando endpoint: GET /groups ou GET /chats?type=group")

endpoints_to_try = [
    "/groups",
    "/chats",
    "/v1/groups",
    "/api/groups",
    "/instance/groups"
]

for endpoint in endpoints_to_try:
    try:
        url = f"{API_URL}{endpoint}"
        print(f"\nTentando: {url}")

        response = httpx.get(url, headers=headers, timeout=10)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            print("✅ SUCESSO! Endpoint encontrado!")
            print(f"Resposta:\n{json.dumps(response.json(), indent=2)}")
            break
        else:
            print(f"❌ Erro: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Exceção: {e}")

# Teste 2: Criar grupo (COMENTADO - descomente quando souber o endpoint)
print("\n\n🔧 Teste 2: Criar grupo")
print("=" * 60)
print("IMPORTANTE: Descomente o código abaixo quando descobrir o endpoint correto")
print("""
# Possíveis formatos:

# Opção 1: Estilo comum
payload = {
    "name": "Teste Grupo API",
    "participants": [ADMIN_NUMBER]
}

# Opção 2: Estilo Z-API
payload = {
    "groupName": "Teste Grupo API",
    "groupParticipants": [ADMIN_NUMBER]
}

# Opção 3: Estilo Whapi
payload = {
    "subject": "Teste Grupo API",
    "participants": [ADMIN_NUMBER]
}

# Endpoints a testar:
endpoints = [
    "/groups",
    "/groups/create",
    "/create-group",
    "/v1/groups/create"
]

for endpoint in endpoints:
    url = f"{API_URL}{endpoint}"
    response = httpx.post(url, headers=headers, json=payload, timeout=10)
    print(f"{endpoint}: {response.status_code}")
""")

# Teste 3: Info de um grupo (você precisa de um group_id existente)
print("\n\n📊 Teste 3: Obter info de um grupo")
print("=" * 60)
print("Substitua 'SEU_GROUP_ID_AQUI' por um ID real de grupo")
print("""
group_id = "120363123456789@g.us"  # Exemplo de formato

endpoints = [
    f"/groups/{group_id}",
    f"/groups/{group_id}/info",
    f"/v1/groups/{group_id}",
]

for endpoint in endpoints:
    url = f"{API_URL}{endpoint}"
    response = httpx.get(url, headers=headers, timeout=10)
    print(f"{endpoint}: {response.status_code}")
    if response.status_code == 200:
        print(json.dumps(response.json(), indent=2))
""")

print("\n\n" + "=" * 60)
print("📝 PRÓXIMOS PASSOS:")
print("=" * 60)
print("1. Execute este script: python test_uazapi.py")
print("2. Veja quais endpoints retornaram 200 (sucesso)")
print("3. Me envie os resultados para eu ajustar o whatsapp_service.py")
print("4. Ou acesse a documentação: https://docs.uazapi.com")
print("\n💡 Dica: Se você tiver acesso ao Postman, veja:")
print("   https://www.postman.com/augustofcs/uazapi/documentation/j48ko4t/uazapi-whatsapp-api-v1-0")
