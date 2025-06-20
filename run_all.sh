#!/bin/bash
set -e

# --- Cleanup from previous run ---
echo "Stopping previous Kafka and ZooKeeper instances if any..."
pkill -f kafka || true
pkill -f zookeeper || true
rm -rf /tmp/zookeeper /tmp/kafka-logs

# ------------ Configuration ------------
# Adjust these paths if your Kafka or project is in a different location:
KAFKA_DIR="$HOME/kafka"
PROJECT_DIR="$HOME/blockhouse"
LOG_DIR="$PROJECT_DIR/logs"

# Topic name
TOPIC_NAME="mock_l1_stream"

# JVM heap options for Kafka and ZK (small values for ~1GB instances)
export KAFKA_HEAP_OPTS="-Xms128m -Xmx256m"

# Snapshot recorder parameters are controlled inside record_snapshots.py:
#   SNAPSHOT_THRESHOLD, MAX_SNAPSHOTS, etc.

# ------------ Prepare logging ------------
mkdir -p "$LOG_DIR"

echo "=== run_all.sh: Starting pipeline ==="
date

# ------------ 1. Start Zookeeper ------------
echo "--- Starting Zookeeper ---"
nohup "$KAFKA_DIR/bin/zookeeper-server-start.sh" "$KAFKA_DIR/config/zookeeper.properties" \
    > "$LOG_DIR/zookeeper.log" 2>&1 &
ZK_PID=$!
echo "Zookeeper PID: $ZK_PID"
# Give Zookeeper time to bind port 2181
sleep 5

# Check Zookeeper process
if ! ps -p $ZK_PID > /dev/null; then
    echo "Error: Zookeeper failed to start. Check $LOG_DIR/zookeeper.log"
    exit 1
fi

# ------------ 2. Start Kafka broker ------------
echo "--- Starting Kafka broker ---"
nohup "$KAFKA_DIR/bin/kafka-server-start.sh" "$KAFKA_DIR/config/server.properties" \
    > "$LOG_DIR/kafka.log" 2>&1 &
KAFKA_PID=$!
echo "Kafka broker PID: $KAFKA_PID"
# Give Kafka time to register with ZK and bind port 9092
sleep 10

# Check Kafka process
if ! ps -p $KAFKA_PID > /dev/null; then
    echo "Error: Kafka broker failed to start. Check $LOG_DIR/kafka.log"
    exit 1
fi

# Optionally verify Kafka is listening on 9092
if ! sudo lsof -iTCP:9092 -sTCP:LISTEN > /dev/null; then
    echo "Warning: Kafka does not appear to be listening on port 9092. Check logs."
else
    echo "Kafka is listening on port 9092."
fi

# ------------ 3. Create topic if needed ------------
echo "--- Verifying/creating topic: $TOPIC_NAME ---"
# List existing topics
"$KAFKA_DIR/bin/kafka-topics.sh" --bootstrap-server localhost:9092 --list \
    > "$LOG_DIR/kafka_topics_before.txt" 2>&1 || true

if grep -q "^${TOPIC_NAME}$" "$LOG_DIR/kafka_topics_before.txt"; then
    echo "Topic '$TOPIC_NAME' already exists."
else
    echo "Creating topic '$TOPIC_NAME'..."
    "$KAFKA_DIR/bin/kafka-topics.sh" --bootstrap-server localhost:9092 \
        --create --topic "$TOPIC_NAME" --partitions 1 --replication-factor 1 \
        > "$LOG_DIR/kafka_create_topic.log" 2>&1
    echo "Topic creation log:"
    cat "$LOG_DIR/kafka_create_topic.log"
fi

# ------------ 4. Start producer ------------
echo "--- Starting producer (stream_l1_to_kafka.py) ---"
cd "$PROJECT_DIR"
nohup python3 stream_l1_to_kafka.py > "$LOG_DIR/producer.log" 2>&1 &
PRODUCER_PID=$!
echo "Producer PID: $PRODUCER_PID"
# Wait briefly so it can connect and start sending
sleep 2

# Optionally check producer log for errors
sleep 3
if grep -i "error" "$LOG_DIR/producer.log" | grep -v "Ignoring" >/dev/null; then
    echo "Warning: Producer log contains 'error'. Check $LOG_DIR/producer.log"
fi

# ------------ 5. Run snapshot recorder ------------
echo "--- Running snapshot recorder (record_snapshots.py) ---"
cd "$PROJECT_DIR"
# Run in foreground so we know when it completes
python3 record_snapshots.py 2>&1 | tee "$LOG_DIR/record_snapshots.out"

# After recorder exits, ensure snapshots.json exists and is non-empty
SNAPSHOT_FILE="$PROJECT_DIR/snapshots.json"
if [ ! -f "$SNAPSHOT_FILE" ]; then
    echo "Error: $SNAPSHOT_FILE not found. Aborting."
    exit 1
fi
if [ ! -s "$SNAPSHOT_FILE" ]; then
    echo "Error: $SNAPSHOT_FILE is empty. Aborting."
    exit 1
fi
echo "Recorded snapshots to $SNAPSHOT_FILE (size: $(stat -c%s "$SNAPSHOT_FILE") bytes)."

# ------------ 6. Run backtest & parameter search ------------
echo "--- Running backtest & parameter search (backtest_driver.py) ---"
cd "$PROJECT_DIR"
python3 backtest_driver.py 2>&1 | tee "$LOG_DIR/backtest_driver.out"

# Check outputs existence
if [ -f "$PROJECT_DIR/execution_report.json" ]; then
    echo "Found execution_report.json"
else
    echo "Warning: execution_report.json not found."
fi
# ------------ 7. Summary ------------
echo
echo "=== run_all.sh Summary ==="
echo "Zookeeper PID: $ZK_PID  (logs: $LOG_DIR/zookeeper.log)"
echo "Kafka PID:     $KAFKA_PID  (logs: $LOG_DIR/kafka.log)"
echo "Producer PID:  $PRODUCER_PID  (logs: $LOG_DIR/producer.log)"
echo "Snapshot recorder log: $LOG_DIR/record_snapshots.out"
echo "Backtest log:          $LOG_DIR/backtest_driver.out"
echo "Snapshots file:        $SNAPSHOT_FILE"
echo "Execution report:      $PROJECT_DIR/execution_report.json"
echo "Full grid results:     $PROJECT_DIR/output.json"
echo "Kafka topics before:   $LOG_DIR/kafka_topics_before.txt"
echo
date
echo "=== run_all.sh complete ==="
