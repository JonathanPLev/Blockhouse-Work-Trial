#!/bin/bash
set -e

echo "Updating system packages..."
sudo dnf update -y

# 1. Add swap if not already present
# Check for existing swap
if ! sudo swapon --show | grep -q '^/swapfile'; then
  echo "No swap found. Creating 1 GiB swapfile..."
  # Attempt fallocate; if not available, fallback to dd
  if command -v fallocate >/dev/null 2>&1; then
    sudo fallocate -l 1G /swapfile
  else
    sudo dd if=/dev/zero of=/swapfile bs=1M count=1024 status=progress
  fi
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
  echo "Swap created and enabled."
else
  echo "Swap already exists:"
  sudo swapon --show
fi

echo "Installing Java (required for Kafka)..."
sudo dnf install -y java-1.8.0-amazon-corretto

echo "Java version:"
java -version

echo "Installing Python and pip..."
sudo dnf install -y python3 python3-pip
pip3 install --user pandas confluent-kafka

echo "Downloading Kafka 3.6.0..."
wget https://dlcdn.apache.org/kafka/3.9.1/kafka_2.13-3.9.1.tgz
tar -xzf kafka_2.13-3.9.1.tgz
mv kafka_2.13-3.9.1 kafka
rm kafka_2.13-3.9.1.tgz

echo "Kafka installed in ~/kafka"

echo "Creating project directory..."
mkdir -p ~/blockhouse
cd ~/blockhouse

echo "Setup complete."
echo
echo "To start Zookeeper:"
echo "  cd ~/kafka && bin/zookeeper-server-start.sh config/zookeeper.properties"
echo
echo "To start Kafka:"
echo "  cd ~/kafka && bin/kafka-server-start.sh config/server.properties"
echo
echo "Place your project files in ~/blockhouse or use scp to upload them from your local machine."
