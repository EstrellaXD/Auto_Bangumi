#!/bin/bash

# Check old version
if [ -f /config/bangumi.json ]; then
    mv /config/bangumi.json /app/data/bangumi.json
fi


umask ${UMASK}
python3 main.py
