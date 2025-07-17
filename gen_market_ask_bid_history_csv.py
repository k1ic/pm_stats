import os
import json
import csv
import argparse
from datetime import datetime
import pytz

def format_time(timestamp_ms):
    """将时间戳（毫秒）格式化为 MM:SS.mmm"""
    dt = datetime.utcfromtimestamp(int(timestamp_ms) / 1000.0)
    return dt.strftime('%M:%S.%f')[:-3]

def process_json_file(filepath):
    with open(filepath, 'r') as f:
        data = json.load(f)

    timestamp = data.get('timestamp', '0')
    time = format_time(timestamp)

    bids = data.get('bids', [])
    asks = data.get('asks', [])

    asks_reversed = list(reversed(asks))[:9]
    ask_prices = [float(a.get('price', 0)) for a in asks_reversed]
    ask_sizes = [float(a.get('size', 0)) for a in asks_reversed]
    ask_prices += [0] * (9 - len(ask_prices))
    ask_sizes += [0] * (9 - len(ask_sizes))

    bid_reversed = list(reversed(bids))[:9]
    bid_prices = [float(a.get('price', 0)) for a in bid_reversed]
    bid_sizes = [float(a.get('size', 0)) for a in bid_reversed]
    bid_prices += [0] * (9 - len(bid_prices))
    bid_sizes += [0] * (9 - len(bid_sizes))

    spread = round(float(asks[-1]['price']) - float(bids[-1]['price']), 2) if asks and bids else 0

    row = [time, spread]
    for p, s in zip(ask_prices, ask_sizes):
        row.extend([p, s])
    for p, s in zip(bid_prices, bid_sizes):
        row.extend([p, s])

    return row

def process_hour(symbol, base_dir, yymmdd, hour):
    output_fields = ['time', 'spread']
    for i in range(1, 10):
        output_fields.extend([f'ask{i}_price', f'ask{i}_size'])
    for i in range(1, 10):
        output_fields.extend([f'bid{i}_price', f'bid{i}_size'])

    for side in ['0', '1']:
        side_name = 'Up' if side == '0' else 'Down'
        input_dir = os.path.join(base_dir, symbol, yymmdd, 'row_data', hour, side)
        if not os.path.exists(input_dir):
            continue

        json_files = sorted(
            [f for f in os.listdir(input_dir) if f.endswith('.json')],
            key=lambda x: int(x.replace('.json', ''))
        )

        rows = []
        for filename in json_files:
            filepath = os.path.join(input_dir, filename)
            try:
                row = process_json_file(filepath)
                rows.append(row)
            except Exception as e:
                print(f"Error processing {filepath}: {e}")

        if rows:
            output_dir = os.path.join(base_dir, symbol, yymmdd, 'order_book_history')
            os.makedirs(output_dir, exist_ok=True)

            output_file = os.path.join(output_dir, f"{yymmdd}_{hour}_{side_name}_asks_bids_histroy.csv")
            with open(output_file, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(output_fields)
                writer.writerows(rows)
            print(f"Saved: {output_file}")

def get_current_et_hour_info():
    """返回当前ET时区的日期字符串和小时字符串，如 ('20250717', '3pm')"""
    et = pytz.timezone('US/Eastern')
    now_et = datetime.now(et)
    yymmdd = now_et.strftime('%Y%m%d')
    hour = now_et.strftime('%I%p').lstrip('0').lower()  # 12小时制，如 '3pm'
    return yymmdd, hour

def main():
    parser = argparse.ArgumentParser(description='Process current ET hour order book data.')
    parser.add_argument('--symbol', choices=['btc', 'eth', 'sol', 'xrp'], required=True, help='Crypto symbol (e.g. btc, eth)')
    args = parser.parse_args()

    base_dir = 'price_data'
    symbol = args.symbol
    yymmdd, hour = get_current_et_hour_info()

    print(f"Processing symbol={symbol}, date={yymmdd}, hour={hour} (ET)...")
    process_hour(symbol, base_dir, yymmdd, hour)

if __name__ == '__main__':
    main()
