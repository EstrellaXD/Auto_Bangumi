from module.utils import path_to_bangumi


def test_path_to_bangumi():
    # Test for unix-like path
    path = "/Downloads/Bangumi/Kono Subarashii Sekai ni Shukufuku wo!/Season 2/"
    bangumi_name, season = path_to_bangumi(path, "/Downloads/Bangumi")
    assert bangumi_name == "Kono Subarashii Sekai ni Shukufuku wo!"
    assert season == 2
