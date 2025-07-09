import requests
from datetime import datetime, timedelta
import pytz
import os
import json

def get_et_hour_slug():
    # 当前北京时间
    now_bj = datetime.now(pytz.timezone("Asia/Shanghai"))

    # 转为美东时间（支持夏令时自动处理）
    eastern = pytz.timezone("US/Eastern")
    now_et = now_bj.astimezone(eastern)

    # 获取当前ET小时开始时间
    et_hour_start = now_et.replace(minute=0, second=0, microsecond=0)

    # 构造slug
    slug = f"bitcoin-up-or-down-{et_hour_start.strftime('%B').lower()}-{et_hour_start.day}-" \
           f"{et_hour_start.strftime('%-I%p').lower()}-et"

    # 日期和小时目录
    #date_str = now_bj.strftime('%Y%m%d')
    date_str = now_et.strftime('%Y%m%d')
    hour_str = et_hour_start.strftime('%-I%p').lower()

    return slug, date_str, hour_str, et_hour_start

def fetch_clob_token_ids(slug, date_str, hour_str):
    url = f"https://gamma-api.polymarket.com/markets?slug={slug}"
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()

    dir_path = os.path.join('btc', date_str, hour_str)
    os.makedirs(dir_path, exist_ok=True)
    file_path = os.path.join(dir_path, "markets.json")
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)

    return data[0]["clobTokenIds"]

def fetch_and_save_price_history(token_id, date_str, hour_str):
    url = f"https://clob.polymarket.com/prices-history?market={token_id}&interval=1h&fidelity=1"
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()

    dir_path = os.path.join('btc', date_str, hour_str)
    os.makedirs(dir_path, exist_ok=True)
    file_path = os.path.join(dir_path, f"{token_id}.json")

    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)
    #print(f"Saved to {file_path}")

def main():
    slug, date_str, hour_str, et_hour_start = get_et_hour_slug()
    #print(f"Slug: {slug}")

    try:
        clob_token_ids = fetch_clob_token_ids(slug, date_str, hour_str)
        #print(f"clobTokenIds: {clob_token_ids}")
    except Exception as e:
        print(f"Error fetching clobTokenIds: {e}")
        return

    for token_id in json.loads(clob_token_ids):
        try:
            fetch_and_save_price_history(token_id, date_str, hour_str)
        except Exception as e:
            print(f"Error fetching price history for {token_id}: {e}")

if __name__ == "__main__":
    main()
