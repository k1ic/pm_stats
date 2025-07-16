# * * * * * cd /var/www/pm_stats && /usr/bin/python3 gen_hourly_midpoint_graph.py btc > /dev/null 2>&1
import os
import datetime
import matplotlib.pyplot as plt
import pytz
import json
import requests
from decimal import Decimal
from matplotlib.colors import to_hex

def get_distinct_colors(n):
    cmaps = ['tab10', 'Set1', 'Set2', 'Set3', 'Dark2', 'Paired']
    colors = []
    for cmap_name in cmaps:
        cmap = plt.get_cmap(cmap_name)
        for i in range(cmap.N):
            colors.append(to_hex(cmap(i)))
            if len(colors) >= n:
                return colors
    return colors[:n]

def hour_to_label(hour):
    if hour == 0:
        return "12am"
    elif hour < 12:
        return f"{hour}am"
    elif hour == 12:
        return "12pm"
    else:
        return f"{hour - 12}pm"

def plot_chart(data_list, start_hour, end_hour, filename, title):
    fig, ax_left = plt.subplots(figsize=(15, 8))
    ax_left.set_title(title)
    ax_left.set_xlabel("Minute (0-60)")
    ax_left.set_ylabel("Midpoint (scaled to cents)")
    ax_left.set_xlim(0, 60)
    ax_left.set_ylim(0, 100)
    ax_left.set_xticks(range(0, 61, 2))
    ax_left.set_yticks(range(0, 101, 5))
    ax_left.grid(True)

    ax_left.axhline(y=20, color='black', linestyle='--', linewidth=2)
    ax_left.axhline(y=40, color='black', linestyle='-.', linewidth=1)
    ax_left.axhline(y=45, color='black', linestyle='-.', linewidth=1)
    ax_left.axhline(y=50, color='black', linestyle='--', linewidth=2)
    ax_left.axhline(y=70, color='black', linestyle='-.', linewidth=1)
    ax_left.axhline(y=75, color='black', linestyle='-.', linewidth=1)
    ax_left.axhline(y=80, color='black', linestyle='--', linewidth=2)

    ax_left.axvline(x=46, color='black', linestyle=':', linewidth=2)
    ax_left.axvline(x=50, color='black', linestyle=':', linewidth=2)
    ax_left.axvline(x=52, color='black', linestyle=':', linewidth=1)
    ax_left.axvline(x=58, color='black', linestyle=':', linewidth=1)

    ax_right = ax_left.twinx()
    ax_right.set_ylim(100, 0)
    ax_right.set_yticks(range(0, 101, 5))
    ax_right.set_ylabel("Midpoint (reversed)")

    colors = get_distinct_colors(len(data_list))
    for idx, (label, x, y) in enumerate(data_list):
        ax_left.plot(x, y, label=label, color=colors[idx], linewidth=2)

    if data_list:
        ax_left.legend(loc='upper left', ncol=2, fontsize='small')

    fig.tight_layout()
    plt.savefig(filename)
    plt.close()
    print(f"[DONE] Saved: {filename}")

def fetch_token_info(symbol, hour_et):
    symbol_slug_map = {
        "btc": "bitcoin",
        "eth": "ethereum",
        "sol": "solana",
        "xrp": "xrp"
    }
    symbol_slug = symbol_slug_map.get(symbol, "unknown")

    hour_12 = hour_et.hour % 12 or 12
    am_pm = "am" if hour_et.hour < 12 else "pm"
    slug = f"{symbol_slug}-up-or-down-{hour_et.strftime('%B').lower()}-{hour_et.day}-{hour_12}{am_pm}-et"

    try:
        url = f"https://gamma-api.polymarket.com/markets?slug={slug}"
        response = requests.get(url)
        response.raise_for_status()
        market = response.json()[0]

        # 保存 market.json 文件
        date_str = hour_et.strftime("%Y%m%d")
        hour_str = f"{hour_et.hour % 12 or 12}{'am' if hour_et.hour < 12 else 'pm'}"
        base_dir = os.path.join("midpoint", symbol, date_str, hour_str)
        os.makedirs(base_dir, exist_ok=True)

        with open(os.path.join(base_dir, "markets.json"), "w") as f:
            json.dump(response.json(), f, indent=2)

        outcomes = json.loads(market["outcomes"])
        prices = json.loads(market["outcomePrices"])
        token_ids = json.loads(market["clobTokenIds"])
        max_index = prices.index(max(prices, key=lambda x: Decimal(x)))
        return token_ids[max_index], outcomes[max_index], prices[max_index]
    except Exception as e:
        print(f"[ERROR] Failed to fetch or parse market: {slug} -> {e}")
        return None, None, None

def load_midpoint_data(symbol, date_str, hour_str, token_id, start_ts, end_ts):
    base_dir = os.path.join("midpoint", symbol, date_str, hour_str)
    file_path = os.path.join(base_dir, f"{token_id}.data")
    if not os.path.exists(file_path):
        return None

    try:
        with open(file_path) as f:
            lines = f.readlines()
        x_vals, y_vals = [], []
        for line in lines:
            ts_str, price_str = line.strip().split(",")
            ts = int(ts_str)
            price = float(price_str)
            if start_ts <= ts < end_ts:
                minute = (ts - start_ts) / 60
                x_vals.append(minute)
                y_vals.append(price * 100)
        return x_vals, y_vals
    except Exception as e:
        print(f"[WARN] Error reading {file_path}: {e}")
        return None

def main(symbol: str):
    eastern = pytz.timezone("US/Eastern")
    now_et = datetime.datetime.now(pytz.utc).astimezone(eastern)
    today_et = now_et.replace(hour=0, minute=0, second=0, microsecond=0)

    # 当前时间的小时和分钟
    current_hour = now_et.hour
    current_minute = now_et.minute

    date_str = today_et.strftime("%Y%m%d")

    grouped_data = {
        (0, 5): [],
        (6, 11): [],
        (12, 17): [],
        (18, 23): []
    }

    skip_groups = set()
    if current_hour >= 6 and current_minute >= 1:
        skip_groups.add((0, 5))
    if current_hour >= 12 and current_minute >= 1:
        skip_groups.add((6, 11))
    if current_hour >= 18 and current_minute >= 1:
        skip_groups.add((12, 17))

    for hour in range(0, current_hour + 1):
        # 如果该小时属于某个 skip group，直接跳过
        skip = False
        for group in skip_groups:
            if group[0] <= hour <= group[1]:
                skip = True
                break
        if skip:
            continue

        hour_dt = today_et + datetime.timedelta(hours=hour)
        hour_str = f"{hour % 12 or 12}{'am' if hour < 12 else 'pm'}"

        token_id, outcome_label, outcome_price = fetch_token_info(symbol, hour_dt)
        if not token_id:
            continue

        base_dir = os.path.join("midpoint", symbol, date_str, hour_str)
        if not os.path.exists(base_dir):
            continue

        file_path = os.path.join(base_dir, f"{token_id}.data")
        start_ts = int(hour_dt.timestamp())

        # 若是当前小时，只取到当前分钟；否则取整小时
        if hour == current_hour:
            end_ts = int(now_et.timestamp())
        else:
            end_ts = start_ts + 3600

        result = load_midpoint_data(symbol, date_str, hour_str, token_id, start_ts, end_ts)
        if result is None:
            continue

        x_vals, y_vals = result
        label = f"{hour_to_label(hour)}_{outcome_label}_{round(float(outcome_price), 3)}"

        for (start_h, end_h), data_list in grouped_data.items():
            if start_h <= hour <= end_h and len(data_list) < 6:
                data_list.append((label, x_vals, y_vals))
                break

    output_dir = os.path.join("imgs", symbol, date_str)
    os.makedirs(output_dir, exist_ok=True)

    for (start_h, end_h), data_list in grouped_data.items():
        if not data_list:
            continue
        title = f"{date_str} {symbol.upper()} Hourly ET {start_h:02d}-{end_h:02d}(Midpoint Based)"
        filename = os.path.join(output_dir, f"{date_str}-{symbol}-hourly-et-{start_h:02d}-{end_h:02d}_midpoint.png")
        plot_chart(data_list, start_h, end_h, filename, title)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate midpoint chart")
    parser.add_argument("symbol", choices=["btc", "eth", "xrp", "sol"], help="Symbol name (e.g., btc)")
    args = parser.parse_args()
    main(args.symbol)
