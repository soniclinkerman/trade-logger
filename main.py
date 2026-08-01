import time

import requests
from datetime import date, datetime,timedelta,time as dt_time
from dotenv import load_dotenv
from notion import sync_trades

import os
BASE_URL = "https://api.topstepx.com/api"
CONTRACT_TYPE = {0: "Long", 1: "Short"}

def login(user_name,api_key):
    response = requests.post(f'{BASE_URL}/Auth/loginKey', json={"userName": user_name, "apiKey": api_key})
    data = response.json()
    if data["success"] is False:
        raise Exception("Login failed")
    token = data['token']
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

def group_trades(trades: object) -> list:
    formatted_trades = []
    open_trades = {}
    trade_count = 0

    for trade in trades:
        contract = trade["contractId"].split(".")[3]
        trade_type = CONTRACT_TYPE[int(trade['side'])]

        if contract not in open_trades:
            trade_count+=1
            open_trades[contract] = {
                "contract_type": contract,
                "id": trade["id"],
                "type": trade_type,
                "trade_number": trade_count,
                "entryPrice": trade["price"],
                "contracts": trade["size"],
                "entryTime": trade["creationTimestamp"],
                "entry_notional": trade["size"] * trade["price"],
                "entry_size": trade["size"],
                "pnl_total": 0
            }
        else:
            td = open_trades[contract]
            if trade_type == td["type"]:
                td["entry_notional"] += trade["size"] * trade["price"]
                td["entry_size"] += trade["size"]
                td["contracts"] += trade["size"]
            else:
                td["pnl_total"] += trade["profitAndLoss"]
                td["contracts"] -= trade["size"]

            if td["contracts"] == 0:
                td["id"] = trade["id"]
                td["exitTime"] = trade["creationTimestamp"]
                td["exitPrice"] = trade["price"]
                td["profitLoss"] = td["pnl_total"]
                td["entryPrice"] = td["entry_notional"] / td["entry_size"]
                del td["entry_notional"]
                del td["entry_size"]
                del td["pnl_total"]
                formatted_trades.append(td)
                del open_trades[contract]

    return formatted_trades

def group_trades_by_date(formatted_trades):
    grouped_trades = {}
    for trade in formatted_trades:
        entry_time = trade["entryTime"]
        dt = datetime.fromisoformat(entry_time)
        formatted_date = dt.strftime("%B %d, %Y")
        if formatted_date not in grouped_trades:
            grouped_trades[formatted_date] = []
        grouped_trades[formatted_date].append(trade)
    return grouped_trades

def run(headers):
    # Get Active account
    payload = {"onlyActiveAccounts": True}
    account_request = requests.post(f'{BASE_URL}/Account/search', json=payload, headers=headers)
    if account_request.status_code == 401:
        headers = login(username, api_key)
        return run(headers)


    elif account_request.status_code != 200:
        account_request.raise_for_status()

    accounts = account_request.json().get('accounts', [])

    if not accounts:
        print("No active accounts found")
        return headers
    account = accounts[0]

    # Get Trades (CME session: 6 PM ET to 5 PM ET next day)
    today = date.today()
    session_start = datetime.combine(today, dt_time(22, 0))
    session_end = datetime.combine(today + timedelta(days=1), dt_time(21, 0))
    # session_start = datetime.combine(date(2026, 7, 26), dt_time(22, 0))  # 6 PM EDT in UTC
    # session_end = datetime.combine(date(2026, 7, 27), dt_time(21, 0))
    trade_payload = {"accountId": account["id"], "startTimestamp": session_start.isoformat(),
                     "endTimestamp": session_end.isoformat()}
    trade_response = requests.post(f'{BASE_URL}/Trade/search', json=trade_payload, headers=headers)
    if trade_response.status_code == 401:
        headers = login(username, api_key)
        return run(headers)
    elif trade_response.status_code != 200:
        print("Error:", trade_response.json())
        return headers

        # Sort it based on creation date
    trades = trade_response.json().get('trades', [])
    trades = sorted(trades, key=lambda trade: trade["creationTimestamp"])

    # Group and Formatted Trades By Date
    formatted_trades = group_trades(trades)
    grouped_trades = group_trades_by_date(formatted_trades)
    sync_trades(grouped_trades)
    return headers

# Load variables from the .env file
load_dotenv()

api_key = os.getenv("TOPSTEP_API_KEY")
username = os.getenv("USERNAME")
headers = login(username, api_key)

while(True):
    headers =run(headers)
    time.sleep(30)
