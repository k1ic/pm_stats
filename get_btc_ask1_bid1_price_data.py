# * * * * * cd /var/www/pm_stats && /usr/bin/python3 get_btc_ask1_bid1_price_data.py > /dev/null 2>&1
import requests
import datetime
import pytz
import time
import os
import csv

BINANCE_KLINE_URL = "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=1"
BINANCE_TICKER_URL = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
POLYMARKET_MARKET_URL = "https://gamma-api.polymarket.com/markets"
POLYMARKET_ORDERBOOK_URL = "https://clob.polymarket.com/book"

ET = pytz.timezone("US/Eastern")
UTC = pytz.utc

def get_open_price():
    res = requests.get(BINANCE_KLINE_URL).json()
    return res[0][1]  # 开盘价

def get_current_price():
    res = requests.get(BINANCE_TICKER_URL).json()
    return res["price"]

def get_et_hour_slug():
    # 本地时间（Asia/Shanghai），换算为 ET 当前小时
    local_now = datetime.datetime.now(pytz.timezone("Asia/Shanghai"))
    et_now = local_now.astimezone(ET)
    et_hour = et_now.replace(minute=0, second=0, microsecond=0)
    slug = f"bitcoin-up-or-down-{et_hour.strftime('%B').lower()}-{et_hour.day}-{et_hour.hour}am-et" \
        if et_hour.hour < 12 else f"bitcoin-up-or-down-{et_hour.strftime('%B').lower()}-{et_hour.day}-{et_hour.hour - 12}pm-et"
    return slug, et_now

def get_clob_token_ids(slug):
    url = f"{POLYMARKET_MARKET_URL}?slug={slug}"
    res = requests.get(url).json()
    if not res:
        return []
    item = res[0]
    try:
        return eval(item["clobTokenIds"])  # 原字段是 JSON string
    except:
        return []

def get_last_ask_bid(token_id):
    url = f"{POLYMARKET_ORDERBOOK_URL}?token_id={token_id}"
    res = requests.get(url).json()
    asks = res.get("asks", [])
    bids = res.get("bids", [])

    last_ask = asks[-1] if asks else None
    last_bid = bids[-1] if bids else None
    return last_ask, last_bid

def write_to_csv(et_time, open_price, current_price, up_ask, down_ask, up_bid, down_bid):
    date_str = et_time.strftime('%Y%m%d')
    hour_str = et_time.strftime('%-I%p').lower()  # e.g. 5am
    time_str = et_time.strftime('%Y%m%d_%H:%M:%S')
    dir_path = f"price_data/btc/{date_str}"
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
    for i in range(3):
        try:
            open_price = get_open_price()
            current_price = get_current_price()
            slug, et_time = get_et_hour_slug()
            token_ids = get_clob_token_ids(slug)
            if len(token_ids) < 2:
                print(f"[{i}] Not enough token_ids found")
                continue
            up_ask, up_bid = get_last_ask_bid(token_ids[0])
            down_ask, down_bid = get_last_ask_bid(token_ids[1])

            write_to_csv(et_time, open_price, current_price, up_ask, down_ask, up_bid, down_bid)
            print(f"[{i}] Data written for {slug}")
        except Exception as e:
            print(f"[{i}] Error: {e}")
        time.sleep(10)

if __name__ == "__main__":
    main()
