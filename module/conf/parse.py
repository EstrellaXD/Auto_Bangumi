import argparse


def parse():
    parser = argparse.ArgumentParser(
        prog="Auto Bangumi",
        description="""
        本项目是基于 Mikan Project、qBittorrent 的全自动追番整理下载工具。
        只需要在 Mikan Project 上订阅番剧，就可以全自动追番。
        并且整理完成的名称和目录可以直接被 Plex、Jellyfin 等媒体库软件识别，
        无需二次刮削。""",
    )

    parser.add_argument("-d", "--debug", action="store_true", help="debug mode")
    return parser.parse_args()