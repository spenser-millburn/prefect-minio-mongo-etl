#!/bin/bash

# Shell script to run a Python script every 5 minutes

while true; do
    python3 collector.py
    sleep 300
done
