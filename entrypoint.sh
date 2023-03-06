#!/bin/bash

# Check old version
if [ -f /config/bangumi.json ]; then
    mv /config/bangumi.json /data/bangumi.json
fi

# Link config
if [ ! -d /app/config ]; then
    ln -s /config /app/config
fi
if [ ! -d /app/data ]; then
    ln -s /data /app/data
fi

# Set permissions
chown -R ${PUID}:${PGID} /config /data /app

umask ${UMASK}

exec su-exec ${PUID}:${PGID} dumb-init python3 main.py