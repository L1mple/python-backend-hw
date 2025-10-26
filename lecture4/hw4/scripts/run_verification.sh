#!/usr/bin/env bash
set -e
python -m scripts.verify_isolation
echo "----- log.txt -----"
cat log.txt