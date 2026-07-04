#!/bin/bash
# shellcheck shell=bash

umask ${UMASK}

if [ -f /config/bangumi.json ]; then
    mv /config/bangumi.json /app/data/bangumi.json
    # Created as root by the mv; the gated chown below may skip the tree walk,
    # so fix this one legacy file explicitly.
    chown ab:ab /app/data/bangumi.json
fi

groupmod -o -g "${PGID}" ab
usermod -o -u "${PUID}" ab

# 重启循环让 shell 站在 tini 和应用之间，因此必须自己转发信号并等待
# 应用退出，否则 docker stop 时 shell 先死、tini 跟着退出，python 会被
# SIGKILL 打断（SQLite WAL 来不及落盘）。
child=""
forward_signal() {
    if [ -n "${child}" ]; then
        kill -TERM "${child}" 2>/dev/null
        wait "${child}"
        exit $?
    fi
    exit 0
}
trap forward_signal TERM INT

while true; do
    # 应用持久卷中的在线更新覆盖层（在启动应用前、以 root 运行）。脚本内部已全程
    # 兜底 try/except，这里再加 `|| true`：覆盖层失败绝不能阻断容器启动。
    python /app/boot_overlay.py || true

    # Recursive chown of the mounted volumes is O(files): a large poster cache
    # on a NAS makes it the dominant cost of every container start. Only walk
    # the tree when ownership actually needs fixing — first run or a changed
    # PUID/PGID — recorded by a marker. /home/ab is image-internal and tiny, so
    # chown it every time.
    chown ab:ab -R /home/ab
    own_marker="/app/config/.ab_owner"
    want="${PUID}:${PGID}"
    if [ "$(cat "${own_marker}" 2>/dev/null)" != "${want}" ] ||
        [ "$(stat -c '%u:%g' /app/data 2>/dev/null)" != "${want}" ] ||
        [ "$(stat -c '%u:%g' /app/config 2>/dev/null)" != "${want}" ]; then
        echo "${want}" >"${own_marker}"
        chown ab:ab -R /app/data /app/config
    fi

    su-exec "${PUID}:${PGID}" python main.py &
    child=$!
    wait "${child}"
    status=$?
    child=""

    if [ -f /app/config/updates/.restart ]; then
        rm -f /app/config/updates/.restart
        continue
    fi

    exit "${status}"
done
