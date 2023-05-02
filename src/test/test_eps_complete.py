from module.core.api_func import FullSeasonGet
from module.models import Config


def test_full_season_get():
    settings = Config()
    fsg = FullSeasonGet(settings)

    fsg.get_season_torrents()