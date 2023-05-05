from module.parser.analyser import torrent_parser


def test_torrent_parser():
    file_name = "[Lilith-Raws] Boku no Kokoro no Yabai Yatsu - 01 [Baha][WEB-DL][1080p][AVC AAC][CHT][MP4].mp4"
    folder_name = "我内心的糟糕念头(2023)"
    season = 1
    suffix = ".mp4"
    assert torrent_parser(file_name, folder_name, season, suffix, "pn")[0] == "Boku no Kokoro no Yabai Yatsu S01E01.mp4"
    assert torrent_parser(file_name, folder_name, season, suffix, "advance")[0] == "我内心的糟糕念头(2023) S01E01.mp4"
    assert torrent_parser(file_name, folder_name, season, suffix, "none") == "[Lilith-Raws] Boku no Kokoro no Yabai Yatsu - 01 [Baha][WEB-DL][1080p][AVC AAC][CHT][MP4].mp4"


    file_name = "[Sakurato] Tonikaku Kawaii S2 [01][AVC-8bit 1080p AAC][CHS].mp4"
    folder_name = "总之就是非常可爱(2021)"
    season = 2
    suffix = ".mp4"
    assert torrent_parser(file_name, folder_name, season, suffix, "pn")[0] == "Tonikaku Kawaii S02E01.mp4"
    assert torrent_parser(file_name, folder_name, season, suffix, "advance")[0] == "总之就是非常可爱(2021) S02E01.mp4"

    file_name = "[SweetSub&LoliHouse] Heavenly Delusion - 01 [WebRip 1080p HEVC-10bit AAC ASSx2].mkv"
    folder_name = "天国大魔境(2023)"
    season = 1
    suffix = ".mkv"
    assert torrent_parser(file_name, folder_name, season, suffix, "pn")[0] == "Heavenly Delusion S01E01.mkv"
    assert torrent_parser(file_name, folder_name, season, suffix, "advance")[0] == "天国大魔境(2023) S01E01.mkv"

    file_name = "[SBSUB][Kanojo mo Kanojo][01][GB][1080P](456E234).mp4"
    folder_name = "女友也要有"
    season = 1
    suffix = ".mp4"
    assert torrent_parser(file_name, folder_name, season, suffix, "pn")[0] == "Kanojo mo Kanojo S01E01.mp4"
    assert torrent_parser(file_name, folder_name, season, suffix, "advance")[0] == "女友也要有 S01E01.mp4"

    file_name = "[SBSUB][CONAN][1082][V2][1080P][AVC_AAC][CHS_JP](C1E4E331).mp4"
    folder_name = "名侦探柯南(1996)"
    season = 1
    suffix = ".mp4"
    assert torrent_parser(file_name, folder_name, season, suffix, "pn")[0] == "CONAN S01E1082.mp4"
    assert torrent_parser(file_name, folder_name, season, suffix, "advance")[0] == "名侦探柯南(1996) S01E1082.mp4"

    file_name = "海盗战记 S01E01.mp4"
    folder_name = "海盗战记(2021)"
    season = 1
    suffix = ".mp4"
    assert torrent_parser(file_name, folder_name, season, suffix, "pn")[0] == "海盗战记 S01E01.mp4"
    assert torrent_parser(file_name, folder_name, season, suffix, "advance")[0] == "海盗战记(2021) S01E01.mp4"