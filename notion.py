import  os
import requests
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo
NOTION_URL = "https://api.notion.com/v1"

load_dotenv()
notion_api_key = os.getenv("NOTION_API_KEY")
PARENT_PAGE_ID = os.getenv("NOTION_PARENT_PAGE_ID")
def get_headers():
    headers = {
        "Authorization": f"Bearer {notion_api_key}",
        "Notion-Version": "2026-03-11",
        "Content-Type": "application/json"
    }
    return headers
def create_page(headers,parent_page_id, title):
    response = requests.post(
        f"{NOTION_URL}/pages",
        headers=headers,
        json={
            "parent": {"type": "page_id", "page_id": parent_page_id},
            "properties": {
                "title": {"title": [{"text": {"content": title}}]}
            }
        }
    )
    return response.json()

def create_database(headers, parent_page_id):
    response = requests.post(
        f"{NOTION_URL}/databases",
        headers=headers,
        json={
            "parent": {"type": "page_id", "page_id": parent_page_id},
            "title": [{"type": "text", "text": {"content": "Trades"}}],
            "is_inline": True,
            "initial_data_source": {
                "properties": {
                    "id": {"type": "number", "number": {"format": "number"}},
                    "trade_number": {"type": "number", "number": {"format": "number"}},
                    "contract_type": {"type": "select", "select": {}},
                    "type": {"type": "select", "select": {}},
                    "entryPrice": {"type": "number", "number": {"format": "number"}},
                    "exitPrice": {"type": "number", "number": {"format": "number"}},
                    "entryTime": {"type": "date", "date": {}},
                    "exitTime": {"type": "date", "date": {}},
                    "profitLoss": {"type": "number", "number": {"format": "number"}}
                }
            }

        }
    )
    return response.json()


def build_trade_blocks(trade):
    return [
        {
            "type": "heading_2",
            "heading_2": {
                "rich_text": [
                    {"text": {"content": f"Trade #{trade['trade_number']} — {trade['contract_type']} {trade['type']}"}}]
            }
        },
        {
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"text": {"content": f"Entry: {trade['entryPrice']} @ {datetime.fromisoformat(trade['entryTime']).astimezone(ZoneInfo("America/New_York")).strftime("%I:%M %p")}"}}]
            }
        },
        {
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"text": {"content": f"Exit: {trade['exitPrice']} @ {datetime.fromisoformat(trade['exitTime']).astimezone(ZoneInfo("America/New_York")).strftime("%I:%M %p")}"}}]
            }
        },
        {
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"text": {"content": f"P&L: ${trade['profitLoss']}"}}]
            }
        },
        {
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"text": {"content": "Reason: "}}]
            }
        },
        {
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"text": {"content": "Results: "}}]
            }
        },
        {
            "type": "divider",
            "divider": {}
        }
    ]

def sync_trades(grouped_trades):
    headers = get_headers()
    response = requests.get(
        f"{NOTION_URL}/blocks/{PARENT_PAGE_ID}/children",
        headers=headers,
    )
    data = response.json()
    existing_pages = {}

    for block in data["results"]:
        if block["type"] == "child_page":
            existing_pages[block["child_page"]["title"]] = block["id"]
    print(existing_pages)
    page_id = None

    for trade_date in grouped_trades:
        if trade_date not in existing_pages:
            new_page =create_page(headers, PARENT_PAGE_ID ,trade_date)
            page_id = new_page["id"]
            print("Page Created")
        else:
            print("Page Already Exists")
            page_id = existing_pages[trade_date]


        response = requests.get(
            f"{NOTION_URL}/blocks/{page_id}/children",
            headers=headers,
        )
        data = response.json()

        # Database Handler
        database_id = None
        for block in data["results"]:
            if block["type"] == "child_database":
                database_id = block["id"]
                print("Database Already Exists")
                break

        if database_id is None:
            new_database = create_database(headers, page_id)
            database_id = new_database["id"]

        # Retrieve data in DB
        response = requests.get(
            f"{NOTION_URL}/databases/{database_id}",
            headers=headers,
        )
        data_source_id = response.json()["data_sources"][0]["id"]

        response = requests.post(
            f"{NOTION_URL}/data_sources/{data_source_id}/query",
            headers=headers,
        )
        results = response.json()

        existing_ids = {
            row["properties"]["id"]["number"]
            for row in results["results"]
            if row["properties"]["id"]["number"] is not None
        }

        blocks = []
        for trade in grouped_trades[trade_date]:
            if trade["id"] not in existing_ids:
                blocks.extend(build_trade_blocks(trade))
                response = requests.post(
                    f"{NOTION_URL}/pages",
                    headers=headers,
                    json={
                        "parent": {"type": "data_source_id", "data_source_id": data_source_id},
                        "properties": {
                            "id": {"number": trade["id"]},
                            # "trade_number": {"number": trade["trade_number"]},
                            "contract_type": {"select": {"name": trade["contract_type"]}},
                            "type": {"select": {"name": trade["type"]}},
                            "entryPrice": {"number": trade["entryPrice"]},
                            "exitPrice": {"number": trade["exitPrice"]},
                            "entryTime": {"date": {"start": trade["entryTime"]}},
                            "exitTime": {"date": {"start": trade["exitTime"]}},
                            "profitLoss": {"number": trade["profitLoss"]}
                        }
                    }
                )

        if blocks:
            requests.patch(
                f"{NOTION_URL}/blocks/{page_id}/children",
                headers=headers,
                json={"children": blocks}
            )


    print("Complete")

