# 网络请求部份
# TMDB 会返回
# mikan 回返回 title, poster, season
from .baseapi import BaseWebPage
from .mikan import LocalMikan, RemoteMikan
from .tmdb import TMDBInfoAPI, TMDBSearchAPI

__all__ = ["LocalMikan", "RemoteMikan", "BaseWebPage", "TMDBInfoAPI", "TMDBSearchAPI"]
