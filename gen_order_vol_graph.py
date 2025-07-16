import os
import json
import argparse
from decimal import Decimal
from datetime import datetime
import pytz
import matplotlib.pyplot as plt

# 解析命令行参数
parser = argparse.ArgumentParser()
parser.add_argument('--date', type=str, help='Date in YYYYMMDD format (ET timezone). If omitted, use current ET date.')
args = parser.parse_args()

# 获取 ET 当前日期
def get_et_date_str():
    et = pytz.timezone('US/Eastern')
    now_et = datetime.now(et)
    return now_et.strftime('%Y%m%d')

# 日期设定
date = args.date if args.date else get_et_date_str()

# 币种列表与路径配置
symbols = ['btc', 'eth', 'sol', 'xrp']
base_path = "midpoint"
output_base = "imgs"

# 小时标签与排序索引
hour_labels = [
    "12am", "1am", "2am", "3am", "4am", "5am",
    "6am", "7am", "8am", "9am", "10am", "11am",
    "12pm", "1pm", "2pm", "3pm", "4pm", "5pm",
    "6pm", "7pm", "8pm", "9pm", "10pm", "11pm"
]
hour_index = {label: i for i, label in enumerate(hour_labels)}

def format_k(value):
    return f"{value / 1000:.1f}K"

# 遍历 symbol 绘图
for symbol in symbols:
    symbol_path = os.path.join(base_path, symbol, date)
    if not os.path.isdir(symbol_path):
        continue

    volume_per_hour = [0] * 24

    for hour_dir in os.listdir(symbol_path):
        if hour_dir not in hour_index:
            continue

        markets_path = os.path.join(symbol_path, hour_dir, "markets.json")
        if not os.path.isfile(markets_path):
            continue

        try:
            with open(markets_path) as f:
                market_data = json.load(f)
                vol = Decimal(market_data[0]["volume"])
                volume_per_hour[hour_index[hour_dir]] += int(vol)
        except Exception as e:
            print(f"[ERROR] {markets_path}: {e}")

    # 绘图
    plt.figure(figsize=(12, 6))
    bars = plt.bar(hour_labels, volume_per_hour, color='cornflowerblue')

    plt.title(f"{date} ET {symbol.upper()} Houly Order Volume(USD)")
    plt.xlabel("Hour (ET)")
    plt.ylabel("Volume (USD)")
    plt.ylim(2000, 80000)
    plt.yticks([2000 + i * 7800 for i in range(11)])
    plt.xticks(rotation=45)
    plt.grid(axis='y', linestyle='--', alpha=0.6)

    # 添加柱顶标注（K）
    for i, v in enumerate(volume_per_hour):
        if v >= 2000:
            plt.text(i, v + 1000, format_k(v), ha='center', va='bottom', fontsize=8)

    # 保存图片
    plt.tight_layout()
    output_dir = os.path.join(output_base, symbol, date)
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{date}_hourly_vol.png")
    plt.savefig(output_file)
    plt.close()
    print(f"[DONE] Saved: {output_file}")
