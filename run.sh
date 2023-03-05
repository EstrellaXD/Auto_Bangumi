#!/bin/bash

# Check old version
if [  ]; then
    mv /config/bangumi.json /data/bangumi.json
fi



umask ${UMASK}
exec su-exec auto_bangumi:auto_bangumi python3 main.py &
exec su-exec auto_bangumi:auto_bangumi python3 api.py
