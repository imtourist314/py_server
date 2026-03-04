#!/bin/bash
# this needs to run with conda  billman

export DB_CONFIG_FILE="${DB_CONFIG_FILE:=./service/config.py}"

python3 -m service.main
