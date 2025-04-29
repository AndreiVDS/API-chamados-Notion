import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

MOVIDESK_API_TOKEN = os.getenv("MOVIDESK_API_TOKEN_TESTES")
NOTION_API_TOKEN = os.getenv("NOTION_API_TOKEN_TESTES")
NOTION_EQUIPAMENTOS_DB = os.getenv("NOTION_EQUIPAMENTOS_DB_TESTES")

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def get_tickets_movidesk():
    tickets = []
    skip = 0
    has_more = True

    while has_more:
        params = {
            "token": MOVIDESK_API_TOKEN,
            "$skip": skip,
            "$top": 100,
            "$orderby": "createdDate desc",
            "$select": "id,subject,status,owner,createdDate,clients,assets",
            "$expand": "owner,clients,assets"
        }

        response = requests.get("https://api.movidesk.com/public/v1/tickets", params=params, timeout=10)

        if response.status_code != 200:
            print(f"❌ Erro ao buscar tickets: {response.status_code} - {response.text}")
            break

        data = response.json()
        if not data:
            has_more = False
            break

        for ticket in data:
            status = ticket.get("status", "").lower()
            ativos = ticket.get("assets", [])
            cliente = ticket["clients"][0]["businessName"] if ticket.get("clients") else None

            if status in ["novo", "em atendimento"] and ativos and cliente:
                tickets.append(ticket)

        skip += 100
        has_more = len(data) == 100

    print(f"📥 {len(tickets)} chamados válidos com ativos encontrados.")
    return tickets

def get_equipamentos_notion():
    equipamentos = {}
    has_more = True
    next_cursor = None

    while has_more:
        payload = {"page_size": 100}
        if next_cursor:
            payload["start_cursor"] = next_cursor

        response = requests.post(
            f"https://api.notion.com/v1/databases/{NOTION_EQUIPAMENTOS_DB}/query",
            headers=NOTION_HEADERS,
            data=json.dumps(payload)
        )

        if response.status_code != 200:
            print("❌ Erro ao consultar equipamentos:", response.text)
            break

        data = response.json()
        for page in data.get("results", []):
            props = page["properties"]
            nome = props.get("Nome", {}).get("title", [{}])[0].get("text", {}).get("content", "")
            if nome:
                equipamentos[nome] = page["id"]

        has_more = data.get("has_more", False)
        next_cursor = data.get("next_cursor")

    print(f"🧾 {len(equipamentos)} equipamentos carregados do Notion.")
    return equipamentos

def atualizar_status_equipamento(equipamentos_notion, ativos_ocupados_por_usuario):
    for nome, page_id in equipamentos_notion.items():
        if nome in ativos_ocupados_por_usuario:
            status = "Ocupado"
            cliente = ativos_ocupados_por_usuario[nome]
        else:
            status = "Disponível"
            cliente = ""

        payload = {
            "properties": {
                "Status": {"status": {"name": status}},
                "Utilizado por": {"rich_text": [{"text": {"content": cliente}}]} if cliente else {"rich_text": []}
            }
        }

        response = requests.patch(
            f"https://api.notion.com/v1/pages/{page_id}",
            headers=NOTION_HEADERS,
            data=json.dumps(payload)
        )

        if response.status_code == 200:
            print(f"✅ {nome} atualizado → {status} ({cliente if cliente else '---'})")
        else:
            print(f"❌ Erro ao atualizar {nome}: {response.status_code} - {response.text}")

def sync_equipamentos():
    print("\n🔁 Sincronizando equipamentos com chamados Movidesk...")
    tickets_movidesk = get_tickets_movidesk()
    equipamentos_notion = get_equipamentos_notion()
    ativos_ocupados_por_usuario = {}

    for ticket in tickets_movidesk:
        cliente = ticket["clients"][0]["businessName"] if ticket.get("clients") else None
        for ativo in ticket.get("assets", []):
            ativos_ocupados_por_usuario[ativo["name"]] = cliente

    atualizar_status_equipamento(equipamentos_notion, ativos_ocupados_por_usuario)
    print("✅ Sincronização concluída!\n")

if __name__ == "__main__":
    sync_equipamentos()
