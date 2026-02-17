#!/bin/bash
# Find a base in current system, travel there, and dock

set -e

echo "=== Finding bases in current system ==="
BASE_ID=$(./sm pois --json | jq -r '.result.pois[] | select(.type == "base") | .id' | head -n1)

if [ -z "$BASE_ID" ]; then
    echo "ERROR: No bases found in current system"
    exit 1
fi

echo "Found base: $BASE_ID"

echo -e "\n=== Traveling to base ==="
./sm travel "$BASE_ID"

echo -e "\n=== Waiting for travel to complete ==="
./sm wait

echo -e "\n=== Docking ==="
./sm dock

echo -e "\n=== Final Status ==="
./sm status
