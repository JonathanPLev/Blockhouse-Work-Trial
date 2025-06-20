import pandas as pd
from confluent_kafka import Producer
import time
from datetime import datetime
import json

# --- Kafka Configuration ---
producer = Producer({'bootstrap.servers': 'localhost:9092'}) 
topic = 'mock_l1_stream'

# --- Load and Filter Data ---
df = pd.read_csv('l1_day.csv', parse_dates=['ts_event'])
df['ts_event'] = pd.to_datetime(df['ts_event'], utc=True)

# Filter rows between 13:36:32 and 13:45:14 UTC
start_time = pd.to_datetime("2024-08-01T13:36:32Z")
end_time = pd.to_datetime("2024-08-01T13:45:14Z")
df = df[(df['ts_event'] >= start_time) & (df['ts_event'] <= end_time)]
print(f"Streaming {len(df)} events to Kafka topic '{topic}'...")

# Sort just in case
df = df.sort_values('ts_event')

# --- Stream to Kafka with Time Pacing ---
prev_ts = None

print(f"Streaming {len(df)} events to Kafka topic '{topic}'...")

def delivery_report(err, msg):
    if err is not None:
        print(f'❌ Delivery failed: {err}')
    else:
        print(f'✅ Delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}')

for _, row in df.iterrows():
    # Prepare the message
    snapshot = {
        "timestamp": row['ts_event'].isoformat(),
        "publisher_id": row['publisher_id'],
        "ask_px_00": row['ask_px_00'],
        "ask_sz_00": row['ask_sz_00']
    }

    # Log the outgoing snapshot for debug
    print(f"Sending: {snapshot}")

    # Send to Kafka
    producer.produce(topic, value=json.dumps(snapshot), callback=delivery_report)

    # Realistic pacing
    if prev_ts is not None:
        delay = (row['ts_event'] - prev_ts).total_seconds()
        time.sleep(min(delay, 1))  # cap to 1s for practicality
    prev_ts = row['ts_event']

    # Poll for delivery callbacks
    producer.poll(0)

# Ensure everything is sent
producer.flush()
print("✅ Done streaming all messages.")
