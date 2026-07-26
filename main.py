import requests
from datetime import date, datetime,time
from dotenv import load_dotenv
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

def group_trades(trades):
    formatted_trades = []
    trade_data = {}
    is_in_trade = False

    entry_notional = 0
    entry_size = 0
    pnl_total = 0

    for trade in trades:
        trade_type = CONTRACT_TYPE[int(trade['side'])]

        if not is_in_trade:
            trade_data["id"] = trade["id"]
            trade_data["type"] = trade_type
            trade_data["trade_number"] = len(formatted_trades) + 1
            trade_data["entryPrice"] = trade["price"]
            trade_data["contracts"] = trade["size"]
            trade_data["entryTime"] = trade["creationTimestamp"]
            is_in_trade = True
            entry_size = trade["size"]
            entry_notional = entry_size * trade["price"]

        else:
            if trade_type == trade_data["type"]:
                entry_notional += trade["size"] * trade["price"]
                entry_size += trade["size"]
                trade_data["contracts"] += trade["size"]
            else:
                pnl_total += trade["profitAndLoss"]
                trade_data["contracts"] -= trade["size"]

            if trade_data["contracts"] == 0:
                trade_data["exitTime"] = trade["creationTimestamp"]
                trade_data["exitPrice"] = trade["price"]
                trade_data["profitLoss"] = pnl_total
                trade_data["entryPrice"] = entry_notional / entry_size
                formatted_trades.append(trade_data)

                trade_data = {}
                is_in_trade = False
                entry_notional = 0
                entry_size = 0
                pnl_total = 0
    return formatted_trades

# Load variables from the .env file
load_dotenv()

api_key = os.getenv("API_KEY")
username = os.getenv("USERNAME")
headers = login(username, api_key)

# Get Active account
payload = {"onlyActiveAccounts": True}
account_request = requests.post(f'{BASE_URL}/Account/search',json=payload, headers=headers)
account = account_request.json()['accounts'][0]

# Get Trades
start_of_day = datetime.combine(date(2026, 7, 22), time.min)
end_of_day = datetime.combine(date(2026, 7, 23), time.min)
trade_payload = {"accountId": account["id"] ,"startTimestamp": start_of_day.isoformat(), "endTimestamp": end_of_day.isoformat()}
trade_response = requests.post(f'{BASE_URL}/Trade/search',json=trade_payload,  headers=headers)

# Sort it based on creation date
trades = trade_response.json()['trades']
trades = sorted(trades, key=lambda trade: trade["creationTimestamp"])

formatted_trades = group_trades(trades)
print(formatted_trades)