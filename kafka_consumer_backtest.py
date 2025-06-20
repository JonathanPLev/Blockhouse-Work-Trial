from confluent_kafka import Consumer, KafkaError
import json
from collections import defaultdict
from allocator import allocate
from datetime import datetime
import time

# --- Fee & Rebate Schedule ---
VENUE_FEES = {
    "XNAS": {"fee": 0.0030, "rebate": 0.0020},
    "XNYS": {"fee": 0.0025, "rebate": 0.0015},
    "BATS": {"fee": 0.0029, "rebate": 0.0020},
    "EDGX": {"fee": 0.0020, "rebate": 0.0010},
    "ARCA": {"fee": 0.0030, "rebate": 0.0024},
}
DEFAULT_FEE = 0.0025
DEFAULT_REBATE = 0.0015

# --- Kafka Consumer Config ---
conf = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'sor-backtest-group',
    'auto.offset.reset': 'earliest'
}
consumer = Consumer(conf)
consumer.subscribe(['mock_l1_stream'])

# --- Parameters ---
ORDER_SIZE = 5000
lambda_over = 0.1
lambda_under = 0.1
theta_queue = 0.01

# --- State ---
snapshots = defaultdict(list)
total_executed = 0
filled_breakdown = defaultdict(int)

print("Starting SOR backtest...")

try:
    while total_executed < ORDER_SIZE:
        msg = consumer.poll(1.0)
        if msg is None: continue
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                continue
            else:
                print(f"Error: {msg.error()}")
                break

        snapshot = json.loads(msg.value().decode('utf-8'))
        ts = snapshot["timestamp"]
        snapshots[ts].append(snapshot)

        # Only process when snapshot is complete (heuristic: 5+ venues)
        if len(snapshots[ts]) >= 5:
            venues = []
            for entry in snapshots[ts]:
                venue_id = entry["publisher_id"]
                ask = entry["ask_px_00"]
                ask_size = entry["ask_sz_00"]
                fee = VENUE_FEES.get(venue_id, {}).get("fee", DEFAULT_FEE)
                rebate = VENUE_FEES.get(venue_id, {}).get("rebate", DEFAULT_REBATE)
                venues.append({
                    "ask": ask,
                    "ask_size": ask_size,
                    "fee": fee,
                    "rebate": rebate
                })

            unfilled = ORDER_SIZE - total_executed
            split, cost = allocate(unfilled, venues, lambda_over, lambda_under, theta_queue)

            # Execute what we can based on actual venue capacity
            for i, shares in enumerate(split):
                fill = min(shares, venues[i]["ask_size"])
                total_executed += fill
                venue_id = snapshots[ts][i]["publisher_id"]
                filled_breakdown[venue_id] += fill

            print(f"\nTime  Snapshot: {ts}")
            print(f"Split: {split}")
            print(f"Cost: {round(cost, 4)}")
            print(f"Total Executed: {total_executed}\n")

            del snapshots[ts]

except KeyboardInterrupt:
    print("Interrupted.")

finally:
    consumer.close()
    print("\n Final Fill Breakdown:")
    for venue, filled in filled_breakdown.items():
        print(f"{venue}: {filled} shares")
    print(f"Total Executed: {total_executed}")
