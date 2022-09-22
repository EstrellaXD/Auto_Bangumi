#!/bin/bash

sh ./getWebUI.sh

groupmod -o -g "$PGID" bangumi
usermod -o -u "$PUID" bangumi

echo '设置文件夹权限'
chown bangumi:bangumi /config
chown -R bangumi:bangumi /src /usr/local

exec /usr/bin/supervisord -n -c /src/bangumi.conf