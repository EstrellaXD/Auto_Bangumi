#!/bin/bash

echo "设置文件夹权限"
echo "PUID=${PUID}"
echo "PGID=${PGID}"

groupmod -o -g "$PGID" auto_bangumi
usermod -o -u "$PUID" auto_bangumi

chown -R auto_bangumi:auto_bangumi /src /templates /config