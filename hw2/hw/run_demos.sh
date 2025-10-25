#!/bin/bash

cd "$(dirname "$0")"

PYTHON=${PYTHON:-python3}

for script in transaction_demos/[0-9]*.py; do
    echo "=== $script ==="
    $PYTHON "$script"
    echo ""
done

