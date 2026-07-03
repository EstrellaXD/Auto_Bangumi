#!/bin/bash
# shellcheck shell=bash

umask ${UMASK}

if [ -f /config/bangumi.json ]; then
    mv /config/bangumi.json /app/data/bangumi.json
fi

# 应用持久卷中的在线更新覆盖层（在启动应用前、以 root 运行）。脚本内部已全程
# 兜底 try/except，这里再加 `|| true`：覆盖层失败绝不能阻断容器启动。
python /app/boot_overlay.py || true

groupmod -o -g "${PGID}" ab
usermod -o -u "${PUID}" ab

chown ab:ab -R /app/data /app/config /home/ab

exec su-exec "${PUID}:${PGID}" python main.py