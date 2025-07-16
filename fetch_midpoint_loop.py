# 0 * * * * cd /var/www/pm_stats && /usr/bin/python3 fetch_midpoint_loop.py btc > /dev/null 2>&1
# 该脚本在每小时的第0分钟开始执行，持续3600s，先通过 gamma-api.polymarket.com 获取当前在进行的市场的up、down tokenId
# 然后开始执行loop:
# 遍历token_ids，通过 clob.polymarket.com/midpoint 获取传入 tokenId 的midpoint，并写入对应tokenId.data 的文件
# sleep 9s，重复上一步
import os, json
import time
import requests
import argparse
from datetime import datetime, timedelta, timezone
import pytz

symbol_slug_map = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "sol": "solana",
    "xrp": "xrp"
}

# === 时间处理 ===
def get_et_now_rounded_to_hour():
    local_now = datetime.now()
    utc_now = local_now.astimezone(timezone.utc)
    et_tz = pytz.timezone("America/New_York")
    et_now = utc_now.astimezone(et_tz)
    et_rounded = et_now.replace(minute=0, second=0, microsecond=0)
    return et_rounded

def format_slug_and_output_dir(symbol, et_time):
    symbol_slug = symbol_slug_map.get(symbol.lower(), "unknown")
    if symbol_slug == "unknown":
        raise ValueError(f"Unsupported symbol: {symbol}")

    month = et_time.strftime("%B").lower()
    day = et_time.day
    hour_24 = et_time.hour
    hour_12 = hour_24 % 12
    hour_12 = 12 if hour_12 == 0 else hour_12
    ampm = "am" if hour_24 < 12 else "pm"
    hour_str = f"{hour_12}{ampm}"
    date_str = et_time.strftime("%Y%m%d")

    slug = f"{symbol_slug}-up-or-down-{month}-{day}-{hour_str}-et"
    output_dir = os.path.join(f"./midpoint/{symbol}", date_str, hour_str)
    return slug, output_dir

# === 网络请求 ===
def get_token_ids_from_slug(slug):
    url = f"https://gamma-api.polymarket.com/markets?slug={slug}"
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch market data: {response.status_code}")
    data = response.json()
    if not isinstance(data, list) or len(data) == 0:
        raise Exception(f"No market found for slug: {slug}")
    market = data[0]
    clob_token_ids_str = market.get("clobTokenIds", "[]")
    try:
        clob_token_ids = json.loads(clob_token_ids_str)
        return clob_token_ids
    except json.JSONDecodeError:
        raise Exception(f"Invalid clobTokenIds format: {clob_token_ids_str}")

def fetch_midpoint(token_id):
    url = f"https://clob.polymarket.com/midpoint?token_id={token_id}"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Warning: Failed to fetch midpoint for {token_id}, status: {response.status_code}")
        return None
    data = response.json()
    return data

# === 写入文件 ===
def write_midpoint_to_file(token_id, midpoint, output_dir):
    timestamp = int(datetime.now(timezone.utc).timestamp())
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, f"{token_id}.data")
    with open(file_path, "a") as f:
        f.write(f"{timestamp},{midpoint}\n")

# === 主函数 ===
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol", choices=symbol_slug_map.keys(), help="Symbol to track (btc, eth, sol, xrp)")
    args = parser.parse_args()
    symbol = args.symbol.lower()

    INTERVAL = 9
    DURATION = 60 * 60

    et_time = get_et_now_rounded_to_hour()
    try:
        slug, output_dir = format_slug_and_output_dir(symbol, et_time)
    except ValueError as e:
        print(f"[ERROR] {e}")
        return

    print(f"[INFO] Using slug: {slug}")
    print(f"[INFO] Output dir: {output_dir}")

    try:
        token_ids = get_token_ids_from_slug(slug)
        print(f"[INFO] Found token IDs: {token_ids}")
    except Exception as e:
        print(f"[ERROR] Failed to get token IDs: {e}")
        return

    end_time = datetime.now(timezone.utc) + timedelta(seconds=DURATION)

    while datetime.now(timezone.utc) < end_time:
        for token_id in token_ids:
            midpoint_data = fetch_midpoint(token_id)
            if midpoint_data and 'mid' in midpoint_data:
                midpoint = midpoint_data['mid']
                write_midpoint_to_file(token_id, midpoint, output_dir)
                print(f"[{datetime.now().isoformat()}] {token_id}: midpoint={midpoint}")
            else:
                print(f"[{datetime.now().isoformat()}] {token_id}: midpoint unavailable")
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
