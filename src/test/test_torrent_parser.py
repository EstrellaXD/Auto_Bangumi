from module.parser.analyser import torrent_parser


def test_torrent_parser():
    file_name = "[Lilith-Raws] Boku no Kokoro no Yabai Yatsu - 01 [Baha][WEB-DL][1080p][AVC AAC][CHT][MP4].mp4"
    folder_name = "我内心的糟糕念头(2023)"
    season = 1
    suffix = ".mp4"
    assert torrent_parser(file_name, folder_name, season, suffix, "pn") == "Boku no Kokoro no Yabai Yatsu S01E01.mp4"
    assert torrent_parser(file_name, folder_name, season, suffix, "advance") == "我内心的糟糕念头(2023) S01E01.mp4"
    assert torrent_parser(file_name, folder_name, season, suffix, "none") == "[Lilith-Raws] Boku no Kokoro no Yabai Yatsu - 01 [Baha][WEB-DL][1080p][AVC AAC][CHT][MP4].mp4"


    file_name = "[Sakurato] Tonikaku Kawaii S2 [01][AVC-8bit 1080p AAC][CHS].mp4"
    folder_name = "总之就是非常可爱(2021)"
    season = 2
    suffix = ".mp4"
    assert torrent_parser(file_name, folder_name, season, suffix, "pn") == "Tonikaku Kawaii S02E01.mp4"
    assert torrent_parser(file_name, folder_name, season, suffix, "advance") == "总之就是非常可爱(2021) S02E01.mp4"

    file_name = "[SweetSub&LoliHouse] Heavenly Delusion - 01 [WebRip 1080p HEVC-10bit AAC ASSx2].mkv"
    folder_name = "天国大魔境(2023)"
    season = 1
    suffix = ".mkv"
    assert torrent_parser(file_name, folder_name, season, suffix, "pn") == "Heavenly Delusion S01E01.mkv"
    assert torrent_parser(file_name, folder_name, season, suffix, "advance") == "天国大魔境(2023) S01E01.mkv"