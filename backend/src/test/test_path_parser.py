

def test_path_to_bangumi():
    # Test for unix-like path
    from module.downloader.path import TorrentPath
    path = "Downloads/Bangumi/Kono Subarashii Sekai ni Shukufuku wo!/Season 2/"
    bangumi_name, season = TorrentPath()._path_to_bangumi(path)
    assert bangumi_name == "Kono Subarashii Sekai ni Shukufuku wo!"
    assert season == 2


def test_customize_path():
    from pathlib import Path
    from module.downloader.path import TorrentPath
    from module.models import Bangumi
    from module.conf.config import settings
    settings.bangumi_manage.customize_path_pattern = "/${year}/${download_path}/${official_title}"
    settings.downloader.path = "/downloads"
    bangumi = Bangumi()
    bangumi.year = 2022
    bangumi.official_title = "孤独摇滚！"
    save_path = TorrentPath._gen_save_path(bangumi)
    print(save_path)
    assert save_path == str(Path("/2022/downloads/孤独摇滚！"))


def test_customize_path_missing_field():
    from pathlib import Path
    from module.downloader.path import TorrentPath
    from module.models import Bangumi
    from module.conf.config import settings
    settings.bangumi_manage.customize_path_pattern = "/${year}/${download_path}/${official_title}"
    settings.downloader.path = "/downloads"
    bangumi = Bangumi()
    bangumi.official_title = "孤独摇滚！"
    save_path = TorrentPath._gen_save_path(bangumi)
    print(save_path)
    assert save_path == str(Path("/downloads/孤独摇滚！"))
