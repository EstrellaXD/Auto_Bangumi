#!/bin/bash

groupmod -o -g "$PGID" auto_bangumi
usermod -o -u "$PUID" auto_bangumi

echo '设置文件夹权限'
chown auto_bangumi:auto_bangumi /config
chown -R auto_bangumi:auto_bangumi /src