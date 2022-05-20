import qbittorrentapi

qb = qbittorrentapi.Client(host="localhost:8080",username="admin",password="adminadmin")

qb.auth_log_in()
qb.rss_add_feed(url="https://mikanani.me",item_path="自动下载")