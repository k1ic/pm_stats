import os
import json
import datetime
import matplotlib.pyplot as plt
import pytz
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

# 获取当前日期（美国东部时区）
eastern = pytz.timezone("US/Eastern")
now = datetime.datetime.now(eastern)
yesterday = now - datetime.timedelta(days=1)
date_str = yesterday.strftime("%Y%m%d")
base_dir = os.path.join(os.getcwd(), 'btc', date_str)
if not os.path.isdir(base_dir):
    raise FileNotFoundError(f"{base_dir} does not exist")

# 准备每6小时一个分组
groups = {i: [] for i in range(0, 24, 6)}  # {0:[], 6:[], 12:[], 18:[]}

# 遍历每小时数据文件夹
for hour_dir in sorted(os.listdir(base_dir)):
    hour_path = os.path.join(base_dir, hour_dir)
    if not os.path.isdir(hour_path):
        continue

    try:
        with open(os.path.join(hour_path, "markets.json")) as f:
            market_data = json.load(f)[0]

        prices = market_data["outcomePrices"]
        lst = json.loads(prices)
        price_list = [Decimal(x) for x in lst]
        max_index = price_list.index(max(price_list))
        token_ids = json.loads(market_data["clobTokenIds"])
        clob_token_id = token_ids[max_index]

        y_file = os.path.join(hour_path, f"{clob_token_id}.json")
        if not os.path.exists(y_file):
            continue

        with open(y_file) as f:
            history = json.load(f).get("history", [])

        # 解析小时数
        hour_str = hour_dir.lower().replace("am", "").replace("pm", "")
        hour = int(hour_str)
        is_pm = "pm" in hour_dir.lower()
        if is_pm and hour < 12:
            hour += 12
        if not is_pm and hour == 12:
            hour = 0

        hour_dt = eastern.localize(datetime.datetime.strptime(f"{date_str} {hour}", "%Y%m%d %H"))
        start_ts = int(hour_dt.timestamp())
        end_ts = start_ts + 3600

        filtered = [d for d in history if start_ts <= d["t"] < end_ts]
        if not filtered:
            continue

        x_vals = [(d["t"] - start_ts) / 60 for d in filtered]
        y_vals = [d["p"] * 100 for d in filtered]

        group_key = (hour // 6) * 6  # 分组依据
        label = hour_to_label(hour)
        groups[group_key].append((label, x_vals, y_vals))

    except Exception as e:
        print(f"[ERROR] Failed to process {hour_dir}: {e}")
        continue

# 绘图函数
def plot_chart(data_list, start_hour, end_hour, filename, title):
    plt.figure(figsize=(15, 8))
    plt.title(title)
    plt.xlabel("Minute (0-60)")
    plt.ylabel("Price (cents)")
    plt.xlim(0, 60)
    plt.ylim(0, 100)
    plt.xticks(range(0, 61, 2))
    plt.yticks(range(0, 101, 5))
    plt.grid(True)

    plt.axhline(y=20, color='black', linestyle='--', linewidth=2)
    plt.axhline(y=50, color='black', linestyle='--', linewidth=1)
    plt.axhline(y=80, color='black', linestyle='--', linewidth=2)
    plt.axvline(x=33, color='black', linestyle=':', linewidth=2)
    plt.axvline(x=44, color='black', linestyle=':', linewidth=2)

    colors = get_distinct_colors(len(data_list))

    for idx, (label, x, y) in enumerate(data_list):
        plt.plot(x, y, label=label, color=colors[idx], linewidth=2)

    if data_list:
        plt.legend(loc='upper right', ncol=2, fontsize='small')

    plt.tight_layout()
    plt.savefig(filename)
    plt.close()
    print(f"[DONE] Saved: {filename}")

# 输出每个6小时图
for start_hour in range(0, 24, 6):
    data = groups[start_hour]
    if not data:
        continue

    end_hour = start_hour + 5
    start_label = hour_to_label(start_hour)
    end_label = hour_to_label((end_hour + 1) % 24)
    title = f"{date_str} BTC Hourly ET {start_label}–{end_label}"
    filename = f"imgs/{date_str}-btc-hourly-et-{start_hour:02d}-{end_hour:02d}.png"

    plot_chart(data, start_hour, end_hour, filename, title)
