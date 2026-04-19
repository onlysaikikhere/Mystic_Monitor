#!/bin/bash
# A simple wrapper to automate collecting system metrics and training the ML model.
# Usage: ./train_pipeline.sh [SECONDS]

# Default to 60 seconds if no argument is provided
SECONDS=${1:-60}

echo "Collecting data for $SECONDS seconds..."

# Start the collector in the background
python3 ml/collector.py &
COLLECTOR_PID=$!

# Wait for the specified duration
sleep $SECONDS

# Safely terminate the collector
echo "Data collection complete. Stopping collector..."
kill -SIGINT $COLLECTOR_PID 2>/dev/null || kill -9 $COLLECTOR_PID 2>/dev/null

echo "Training ML model..."
python3 ml/train.py

echo "Pipeline complete. model.pkl has been generated."
