#!/bin/bash
# Simple storage workflow (assumes already docked)

set -e

./sm status

echo "./sm cargo"
./sm cargo

echo -e "./sm storage withdraw ore_iron 10"
./sm storage deposit ore_iron 10

echo -e "./sm storage deposit --credits 5"
./sm storage deposit --credits 5

echo -e "./sm storage"
./sm storage

echo -e "./sm storage withdraw --credits 5"
./sm storage withdraw --credits 5

echo -e "./sm status"
./sm status
