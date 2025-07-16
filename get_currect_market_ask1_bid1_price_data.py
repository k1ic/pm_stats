#* * * * * cd /var/www/pm_stats && /usr/bin/python3 get_btc_ask1_bid1_price_data.py > /dev/null 2>&1
# 通过biance、gamma-api.polymarket、clob.polymarket.com 获取当前在进行的market 订单薄的买1、卖1信息，并写入csv
# 脚本每分钟执行一次，每次执行取四轮买1、卖1信息，每轮间隔10s
import requests
import datetime
import pytz
import time
import os
import csv
import sys
import json

ET = pytz.timezone("US/Eastern")
UTC = pytz.utc

symbol_map = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "sol": "solana",
    "xrp": "xrp"
}

def get_open_price(symbol_upper):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol_upper}USDT&interval=1h&limit=1"
    res = requests.get(url).json()
    return res[0][1]  # 开盘价

def get_current_price(symbol_upper):
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol_upper}USDT"
    res = requests.get(url).json()
    return res["price"]

def get_et_hour_slug(slug_base):
    local_now = datetime.datetime.now(pytz.timezone("Asia/Shanghai"))
    et_now = local_now.astimezone(ET)
    et_hour = et_now.replace(minute=0, second=0, microsecond=0)
    hour_label = f"{et_hour.hour}am" if et_hour.hour < 12 else f"{et_hour.hour - 12}pm"
    slug = f"{slug_base}-up-or-down-{et_hour.strftime('%B').lower()}-{et_hour.day}-{hour_label}-et"
    return slug, et_now

def get_clob_token_ids(slug):
    url = f"https://gamma-api.polymarket.com/markets?slug={slug}"
    res = requests.get(url).json()
    if not res:
        return []
    item = res[0]
    try:
        return eval(item["clobTokenIds"])  # 原字段是 JSON string
    except:
        return []

def get_last_ask_bid(token_id, et_time, symbol, token_id_index):
    url = f"https://clob.polymarket.com/book?token_id={token_id}"
    try:
        res = requests.get(url)
        res.raise_for_status()
        data = res.json()
    except Exception as e:
        print(f"[Error] token_id={token_id} fetch failed: {e}")
        return None, None

    # 保存原始 JSON 数据
    timestamp = int(time.time())
    date_str = et_time.strftime('%Y%m%d')
    dir_path = f"price_data/{symbol}/{date_str}/row_data"
    os.makedirs(dir_path, exist_ok=True)
    file_path = os.path.join(dir_path, f"{timestamp}_{token_id_index}.json")
    if data:
        with open(file_path, 'w') as f:
            #json.dump(data, f, indent=2)
            json.dump(data, f, separators=(',', ':'))
    else:
        print(f"[Warning] token_id={token_id} returned empty JSON")

    asks = data.get("asks", [])
    bids = data.get("bids", [])

    last_ask = asks[-1] if asks else None
    last_bid = bids[-1] if bids else None

    return last_ask, last_bid

def write_to_csv(et_time, open_price, current_price, up_ask, down_ask, up_bid, down_bid, symbol):
    date_str = et_time.strftime('%Y%m%d')
    hour_str = et_time.strftime('%-I%p').lower()
    time_str = et_time.strftime('%Y%m%d_%H:%M:%S')
    dir_path = f"price_data/{symbol}/{date_str}"
    file_path = f"{dir_path}/{hour_str}.csv"

    os.makedirs(dir_path, exist_ok=True)
    file_exists = os.path.exists(file_path)

    with open(file_path, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(["time", "open_price", "current_price", "diff", "up_ask_price", "up_ask_size", "down_ask_price", "down_ask_size", "up_bid_price", "up_bid_size", "down_bid_price", "down_bid_size"])

        diff = round(float(current_price) - float(open_price), 2)
        writer.writerow([
            time_str,
            round(float(open_price), 2),
            round(float(current_price), 2),
            diff,
            up_ask.get("price") if up_ask else "",
            up_ask.get("size") if up_ask else "",
            down_ask.get("price") if down_ask else "",
            down_ask.get("size") if down_ask else "",
            up_bid.get("price") if up_bid else "",
            up_bid.get("size") if up_bid else "",
            down_bid.get("price") if down_bid else "",
            down_bid.get("size") if down_bid else ""
        ])

def main():
    if len(sys.argv) != 2 or sys.argv[1].lower() not in symbol_map:
        print("Usage: python script.py [btc|eth|sol|xrp]")
        return

    symbol = sys.argv[1].lower()
    symbol_upper = symbol.upper()
    slug_base = symbol_map[symbol]

    for i in range(4):
        try:
            open_price = get_open_price(symbol_upper)
            current_price = get_current_price(symbol_upper)
            slug, et_time = get_et_hour_slug(slug_base)
            token_ids = get_clob_token_ids(slug)
            if len(token_ids) < 2:
                print(f"[{i}] Not enough token_ids found for {slug}")
                continue

            up_ask, up_bid = get_last_ask_bid(token_ids[0], et_time, symbol, 0)
            down_ask, down_bid = get_last_ask_bid(token_ids[1], et_time, symbol, 1)

            write_to_csv(et_time, open_price, current_price, up_ask, down_ask, up_bid, down_bid, symbol)
            print(f"[{i}] Data written for {slug}")
        except Exception as e:
            print(f"[{i}] Error: {e}")
        time.sleep(10)

if __name__ == "__main__":
    main()
