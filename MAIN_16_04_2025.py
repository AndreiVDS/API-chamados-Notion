import requests
import json
import os
from dotenv import load_dotenv
from telegram_bot import enviar_mensagem_telegram

load_dotenv()

MOVIDESK_API_TOKEN = os.getenv("MOVIDESK_API_TOKEN_TESTES")
NOTION_API_TOKEN = os.getenv("NOTION_API_TOKEN_TESTES")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID_TESTES")

PALAVRAS_CHAVE = [
    "notebook", "notebooks", "caixa de som", "som", "caixinha de som",
    "régua", "régua de energia", "filtro de luz", "extensão",
    "caixa", "reunião", "zoom", "meet", "microfone", "treinamento",
    "reserva", "reservas", "representante", "representantes", "home office", "home", "office"
]

STATUS_VALIDO = {"novo": "Novo", "em atendimento": "Em atendimento"}

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

NOTIFIED_FILE = "chamados_notificados.json"


def carregar_chamados_notificados():
    if not os.path.exists(NOTIFIED_FILE):
        return set()
    with open(NOTIFIED_FILE, "r") as file:
        return set(json.load(file))


def salvar_chamado_notificado(tag):
    chamados = carregar_chamados_notificados()
    chamados.add(tag)
    with open(NOTIFIED_FILE, "w") as file:
        json.dump(list(chamados), file)


def get_tickets_movidesk():
    url = "https://api.movidesk.com/public/v1/tickets"
    tickets = []
    skip = 0
    page_size = 85

    while True:
        params = {
            "token": MOVIDESK_API_TOKEN,
            "$orderby": "createdDate desc",
            "$skip": skip,
            "$top": page_size,
            "$select": "id,subject,status,owner,createdDate,clients,assets",
            "$expand": "owner,clients,assets,actions",
            "$filter": "(status eq 'Novo' or status eq 'Em atendimento')"
        }

        response = requests.get(url, params=params, timeout=30)
        if response.status_code != 200:
            print("❌ Erro ao consultar Movidesk:", response.text)
            break

        data = response.json()
        if not data:
            break

        tickets.extend(data)
        skip += page_size

    return tickets


def get_tickets_notion():
    tickets = {}
    has_more = True
    next_cursor = None

    while has_more:
        payload = {"page_size": 100}
        if next_cursor:
            payload["start_cursor"] = next_cursor

        url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
        response = requests.post(url, headers=NOTION_HEADERS, data=json.dumps(payload))

        if response.status_code != 200:
            print("❌ Erro ao consultar Notion:", response.text)
            break

        data = response.json()
        for page in data.get("results", []):
            props = page["properties"]
            ticket_id = props.get("Chamado", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")
            if ticket_id:
                tickets[ticket_id] = page["id"]

        has_more = data.get("has_more", False)
        next_cursor = data.get("next_cursor")

    return tickets


def delete_ticket_from_notion(page_id, ticket_id):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    payload = {"archived": True}
    response = requests.patch(url, headers=NOTION_HEADERS, data=json.dumps(payload))
    if response.status_code == 200:
        print(f"🗑️ Removido do Notion: Ticket {ticket_id}")
    else:
        print(f"❌ Erro ao remover ticket {ticket_id}: {response.text}")


def criar_ou_atualizar_ticket(ticket, tickets_notion, chamados_notificados):
    ticket_id = str(ticket["id"])
    status_movidesk = ticket.get("status", "").lower()

    if status_movidesk not in STATUS_VALIDO:
        if ticket_id in tickets_notion:
            delete_ticket_from_notion(tickets_notion[ticket_id], ticket_id)
        return

    ativos = ticket.get("assets", [])
    responsavel = ticket.get("owner")
    titulo = ticket.get("subject", "").lower()
    cliente = ticket["clients"][0]["businessName"] if ticket.get("clients") else "Sem cliente"
    data = ticket.get("createdDate", "No data Created")
    descricao = (
        ticket.get("actions", [{}])[0].get("description") or
        ticket.get("justification") or 
        "Sem descrição"
    )   

    tag_problema = f"{ticket_id}_sem_responsavel"
    tag_ok = f"{ticket_id}_atribuição_completa"

    if not responsavel and not ativos and any(palavra in titulo for palavra in PALAVRAS_CHAVE):
        if tag_problema not in chamados_notificados:
            mensagem = (
                f"🚨 Chamado sem atribuição com palavra-chave!\n\n"
                f"🔖 Título: {ticket.get('subject', 'Sem título')}\n"
                f"🆔 Número: `{ticket_id}`\n"
                f"👤 Solicitante: {cliente}\n"
                f"🗓️ Data: `{data}`\n"
            )
            enviar_mensagem_telegram(mensagem)
            salvar_chamado_notificado(tag_problema)

    if responsavel and ativos:
        status_notion = STATUS_VALIDO[status_movidesk]
        notion_data = {
            "title": ticket.get("subject", "Sem título"),
            "id": ticket_id,
            "status": status_notion,
            "client": cliente,
            "responsible": responsavel["businessName"],
            "assets": ", ".join(asset["name"] for asset in ativos),
            "created_date": data
        }

        payload = {
            "properties": {
                "Titulo": {"title": [{"text": {"content": notion_data["title"]}}]},
                "Chamado": {"rich_text": [{"text": {"content": notion_data["id"]}}]},
                "Solicitante": {"rich_text": [{"text": {"content": notion_data["client"]}}]},
                "Responsavel": {"rich_text": [{"text": {"content": notion_data["responsible"]}}]},
                "Ativo": {"rich_text": [{"text": {"content": notion_data["assets"]}}]},
                "Status": {"status": {"name": notion_data["status"]}}
            },
            "children": [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": descricao
                                }
                            }
                        ]
                    }
                }
            ]
        }

        if tag_ok not in chamados_notificados:
            mensagem = (
                f"📢 Chamado Atribuído e registrado no Notion!\n\n"
                f"🔖 Título: {notion_data['title']}\n"
                f"🆔 Número: `{notion_data['id']}`\n"
                f"👤 Solicitante: {notion_data['client']}\n"
                f"👨‍💻 Responsável: {notion_data['responsible']}\n"
                f"💻 Equipamento: {notion_data['assets']}\n"
                f"🗓️ Data: `{notion_data['created_date']}`\n"
            )
            enviar_mensagem_telegram(mensagem)
            salvar_chamado_notificado(tag_ok)

        if ticket_id in tickets_notion:
            url = f"https://api.notion.com/v1/pages/{tickets_notion[ticket_id]}"
            payload_sem_children = dict(payload)  # cópia
            payload_sem_children.pop("children", None)  # remove 'children'
            response = requests.patch(url, headers=NOTION_HEADERS, data=json.dumps(payload_sem_children))
            if response.status_code == 200:
                print(f"🔄 Atualizado ticket {ticket_id}")
            else:
                print(f"❌ Erro ao atualizar {ticket_id}: {response.text}")
        else:
            payload["parent"] = {"database_id": NOTION_DATABASE_ID}
            url = "https://api.notion.com/v1/pages"
            response = requests.post(url, headers=NOTION_HEADERS, data=json.dumps(payload))
            if response.status_code == 200:
                print(f"✅ Criado ticket {ticket_id}")
            else:
                print(f"❌ Erro ao criar {ticket_id}: {response.text}")


def sync_once():
    print(f"✅ DATABASE_ID carregado: {NOTION_DATABASE_ID}")
    print(f"✅ TOKEN Notion: {NOTION_API_TOKEN[:10]}...")
    print("\n🔁 Sincronizando Movidesk com Notion...")

    chamados_notificados = carregar_chamados_notificados()
    tickets_movidesk = get_tickets_movidesk()
    tickets_notion = get_tickets_notion()

    movidesk_ids = set()
    for ticket in tickets_movidesk:
        ticket_id = str(ticket["id"])
        movidesk_ids.add(ticket_id)
        criar_ou_atualizar_ticket(ticket, tickets_notion, chamados_notificados)

    for ticket_id, page_id in tickets_notion.items():
        if ticket_id not in movidesk_ids:
            delete_ticket_from_notion(page_id, ticket_id)

    print("✅ Sincronização finalizada.\n")


if __name__ == "__main__":
    sync_once()
