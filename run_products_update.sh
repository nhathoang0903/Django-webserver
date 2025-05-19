#!/bin/bash

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Create logs directory if it doesn't exist
mkdir -p logs

echo "Starting products update service $(date)" >> logs/products_update_service.log

# Run forever with a 30-minute interval
while true; do
  echo "Running products update at $(date)" >> logs/products_update_service.log
  
  # Run the Python script
  python3 json/updateproductsjson.py
  
  # Sleep for 30 minutes (1800 seconds)
  echo "Sleeping for 30 minutes until next update" >> logs/products_update_service.log
  sleep 1800
done 