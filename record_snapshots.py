from confluent_kafka import Consumer, KafkaError
import json
from collections import defaultdict
from datetime import datetime
import time

# --- Kafka Consumer Setup ---
conf = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'snapshot-dumper',
    'auto.offset.reset': 'earliest'
}
consumer = Consumer(conf)
consumer.subscribe(['mock_l1_stream'])

# --- Config ---
SNAPSHOT_THRESHOLD = 5  # how many venues needed to trigger a snapshot group
MAX_SNAPSHOTS = 100     # or break after N snapshots
grouped_snapshots = []
current_snapshot = defaultdict(list)

print("Recording snapshots from Kafka...")

try:
    while len(grouped_snapshots) < MAX_SNAPSHOTS:
        msg = consumer.poll(1.0)
        if msg is None: continue
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                continue
            else:
                print(f"Error: {msg.error()}")
                break

        quote = json.loads(msg.value().decode('utf-8'))
        ts = quote["timestamp"]
        current_snapshot[ts].append({
            "timestamp": ts,
            "publisher_id": quote["publisher_id"],
            "ask_px_00": quote["ask_px_00"],
            "ask_sz_00": quote["ask_sz_00"]
        })

        # When enough quotes are received for a timestamp, save the snapshot
        if len(current_snapshot[ts]) >= SNAPSHOT_THRESHOLD:
            grouped_snapshots.append(current_snapshot[ts])
            del current_snapshot[ts]
            print(f"✅ Captured snapshot #{len(grouped_snapshots)}")

except KeyboardInterrupt:
    print("Interrupted.")

finally:
    consumer.close()
    with open("snapshots.json", "w") as f:
        json.dump(grouped_snapshots, f, indent=2)
    print(f"\n✅ Saved {len(grouped_snapshots)} snapshots to snapshots.json")
