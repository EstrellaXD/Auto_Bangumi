#!/bin/bash
# shellcheck shell=bash

umask ${UMASK}

# 全局控制变量
SHOULD_STOP=false
PID_FILE="/tmp/autobangumi.pid"

# 信号处理函数
cleanup() {
  echo "收到停止信号，正在清理..."
  SHOULD_STOP=true
  if [ -f "$PID_FILE" ]; then
    pid=$(cat "$PID_FILE")
    if [ -n "$pid" ]; then
      echo "正在停止应用进程 $pid..."
      kill -TERM "$pid" 2>/dev/null
      sleep 5
      # 如果进程仍在运行，强制终止
      if kill -0 "$pid" 2>/dev/null; then
        echo "强制终止应用进程 $pid..."
        kill -KILL "$pid" 2>/dev/null
      fi
    fi
    rm -f "$PID_FILE"
  fi
}

# 设置信号捕获
trap cleanup SIGTERM SIGINT SIGUSR1

if [ -f /config/bangumi.json ]; then
  mv /config/bangumi.json /app/data/bangumi.json
fi

groupmod -o -g "${PGID}" ab
usermod -o -u "${PUID}" ab

chown ab:ab -R /app /home/ab

# 热更新重启循环
while [ "$SHOULD_STOP" != "true" ]; do
  echo "启动 Auto_Bangumi 应用..."
  su-exec "${PUID}:${PGID}" .venv/bin/python src/main.py &
  app_pid=$!
  echo $app_pid >"$PID_FILE"

  # 等待应用结束
  wait $app_pid
  exit_code=$?
  rm -f "$PID_FILE"

  # 根据退出码决定是否重启
  if [ "$SHOULD_STOP" = "true" ]; then
    echo "容器正在停止..."
    break
  elif [ $exit_code -eq 0 ]; then
    echo "应用正常退出，2秒后重启（热更新）..."
    sleep 2
    
    # 在Python进程完全退出后检查更新标志
    if [ -f "/tmp/auto_bangumi_update_ready.flag" ]; then
      echo "检测到更新标志，执行文件替换..."
      
      # 读取更新信息
      extract_path=$(python3 -c "
import json
try:
    with open('/tmp/auto_bangumi_update_ready.flag', 'r') as f:
        data = json.load(f)
    print(data.get('extract_path', ''))
except:
    print('')
" 2>/dev/null || echo "")
      
      if [ -n "$extract_path" ] && [ -d "$extract_path" ]; then
        echo "从 $extract_path 更新应用文件..."
        
        # 更新 src 目录
        if [ -d "$extract_path/src" ]; then
          echo "更新 src 目录..."
          rm -rf /app/src.old 2>/dev/null || true
          [ -d "/app/src" ] && mv /app/src /app/src.old
          cp -r "$extract_path/src" /app/src && echo "src 目录更新成功"
        fi
        
        # 更新 dist 目录  
        if [ -d "$extract_path/dist" ]; then
          echo "更新 dist 目录..."
          rm -rf /app/dist.old 2>/dev/null || true
          [ -d "/app/dist" ] && mv /app/dist /app/dist.old  
          cp -r "$extract_path/dist" /app/dist && echo "dist 目录更新成功"
        fi
        
        # 修复权限并清理
        chown -R ab:ab /app/src /app/dist 2>/dev/null || true
        rm -rf /app/src.old /app/dist.old "$extract_path" 2>/dev/null || true
        echo "文件替换完成！"
      else
        echo "无效的更新路径: $extract_path"  
      fi
      
      # 删除更新标志文件
      rm -f "/tmp/auto_bangumi_update_ready.flag"
      echo "更新处理完成，启动新版本..."
    fi
  else
    echo "应用异常退出 (退出码: $exit_code)，停止容器"
    exit $exit_code
  fi
done

echo "Auto_Bangumi 容器已停止"
exit 0
