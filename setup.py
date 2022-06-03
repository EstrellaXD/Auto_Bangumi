# coding:utf-8

from setuptools import setup, find_packages

setup(
    name="auto_bangumi",  # 包名字
    version="2.4.0b4",  # 包版本
    description="一个全自动追番整理下载工具",
    long_description="""
        本项目是基于 Mikan Project、qBittorrent 的全自动追番整理下载工具。
        只需要在 Mikan Project 上订阅番剧，就可以全自动追番。
        并且整理完成的名称和目录可以直接被 Plex、Jellyfin 等媒体库软件识别，
        无需二次刮削。""",  # 简单描述
    author="Estrella Pan",  # 作者
    author_email="estrellaxd05@gmail.com",  # 作者邮箱
    url="https://github.com/EstrellaXD/Auto_Bangumi",  # 包的主页
    packages=find_packages(where=".", exclude=("tests",), include=('*',)),
    package_data={"auto_bangumi.RssFilter":["*.json"]},
    package_dir={"auto_bangumi":"auto_bangumi"},
    data_files=[("config", ["config/rule.json"])],
    install_requires= [
        "qbittorrent-api",
        "bs4",
        "requests",
        "lxml",
        "zhconv",
    ]
)
