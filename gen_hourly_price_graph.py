import os
import json
import datetime
import matplotlib.pyplot as plt
import pytz
import argparse
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
    ax_left.set_ylabel("Price (cents)")
    ax_left.set_xlim(0, 60)
    ax_left.set_ylim(0, 100)
    ax_left.set_xticks(range(0, 61, 2))
    ax_left.set_yticks(range(0, 101, 5))
    ax_left.grid(True)

    # 辅助线
    ax_left.axhline(y=20, color='black', linestyle='--', linewidth=2)
    ax_left.axhline(y=50, color='black', linestyle='--', linewidth=1)
    ax_left.axhline(y=80, color='black', linestyle='--', linewidth=2)
    ax_left.axvline(x=33, color='black', linestyle=':', linewidth=2)
    ax_left.axvline(x=44, color='black', linestyle=':', linewidth=2)

    # 右侧反向 Y 轴
    ax_right = ax_left.twinx()
    ax_right.set_ylim(100, 0)
    ax_right.set_yticks(range(0, 101, 5))
    ax_right.set_ylabel("Price (cents, reversed)")

    colors = get_distinct_colors(len(data_list))
    for idx, (label, x, y) in enumerate(data_list):
        ax_left.plot(x, y, label=label, color=colors[idx], linewidth=2)

    if data_list:
        ax_left.legend(loc='upper right', ncol=2, fontsize='small')

    fig.tight_layout()
    plt.savefig(filename)
    plt.close()
    print(f"[DONE] Saved: {filename}")

def main(symbol: str):
    eastern = pytz.timezone("US/Eastern")
    now = datetime.datetime.now(eastern)
    date_str = now.strftime("%Y%m%d")

    base_dir = os.path.join(os.getcwd(), symbol, date_str)
    if not os.path.isdir(base_dir):
        raise FileNotFoundError(f"{base_dir} does not exist")

    groups = {i: [] for i in range(0, 24, 6)}

    for hour_dir in sorted(os.listdir(base_dir)):
        hour_path = os.path.join(base_dir, hour_dir)
        if not os.path.isdir(hour_path):
            continue

        try:
            with open(os.path.join(hour_path, "markets.json")) as f:
                market_data = json.load(f)[0]

            prices = json.loads(market_data["outcomePrices"])
            price_list = [Decimal(x) for x in prices]
            max_index = price_list.index(max(price_list))

            token_ids = json.loads(market_data["clobTokenIds"])
            clob_token_id = token_ids[max_index]

            y_file = os.path.join(hour_path, f"{clob_token_id}.json")
            if not os.path.exists(y_file):
                continue

            with open(y_file) as f:
                history = json.load(f).get("history", [])

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

            group_key = (hour // 6) * 6
            label = hour_to_label(hour)
            groups[group_key].append((label, x_vals, y_vals))

        except Exception as e:
            print(f"[ERROR] Failed to process {hour_dir}: {e}")
            continue

    output_dir = os.path.join("imgs", symbol, date_str)
    os.makedirs(output_dir, exist_ok=True)

    for start_hour in range(0, 24, 6):
        data = groups[start_hour]
        if not data:
            continue
        end_hour = start_hour + 5
        title = f"{date_str} {symbol.upper()} Hourly ET {start_hour:02d}–{end_hour:02d}"
        filename = os.path.join(
            output_dir,
            f"{date_str}-{symbol}-hourly-et-{start_hour:02d}-{end_hour:02d}.png"
        )
        plot_chart(data, start_hour, end_hour, filename, title)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate hourly price chart by coin symbol")
    parser.add_argument("symbol", choices=["btc", "eth", "xrp", "sol"], help="Symbol name (e.g., btc, eth)")
    args = parser.parse_args()

    main(args.symbol)
