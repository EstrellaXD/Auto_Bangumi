
from module.parser.analyser import torrent_parser


def test_torrent_parser():
    file_name = "[Lilith-Raws] Boku no Kokoro no Yabai Yatsu - 02 [Baha][WEB-DL][1080p][AVC AAC][CHT][MP4].mp4"
    bf = torrent_parser(file_name)
    assert bf.title == "Boku no Kokoro no Yabai Yatsu"
    assert bf.group == "Lilith-Raws"
    assert bf.episode == 2
    assert bf.season == 1

    file_name = "[Sakurato] Tonikaku Kawaii S2 [03][AVC-8bit 1080p AAC][CHS].mp4"
    bf = torrent_parser(file_name)
    assert bf.title == "Tonikaku Kawaii"
    assert bf.group == "Sakurato"
    assert bf.episode == 3
    assert bf.season == 2

    file_name = "[SweetSub&LoliHouse] Heavenly Delusion - 02 [WebRip 1080p HEVC-10bit AAC ASSx2].mkv"
    bf = torrent_parser(file_name)
    assert bf.title == "Heavenly Delusion"
    assert bf.group == "SweetSub&LoliHouse"
    assert bf.episode == 2
    assert bf.season == 1

    file_name = "[SBSUB][CONAN][1082][V2][1080P][AVC_AAC][CHS_JP](C1E4E331).mp4"
    bf = torrent_parser(file_name)
    assert bf.title == "CONAN"
    assert bf.group == "SBSUB"
    assert bf.episode == 1082
    assert bf.season == 1

    file_name = "海盗战记 (2019) S01E01.mp4"
    bf = torrent_parser(file_name)
    assert bf.title == "海盗战记"
    assert bf.episode == 1
    assert bf.season == 1

    file_name = "海盗战记/海盗战记 S01E01.mp4"
    bf = torrent_parser(file_name)
    assert bf.title == "海盗战记"
    assert bf.episode == 1
    assert bf.season == 1

    file_name = "海盗战记 S01E01.zh-tw.ass"
    sf = torrent_parser(file_name)
    assert sf.title == "海盗战记"
    assert sf.episode == 1
    assert sf.season == 1
    assert sf.language == "zh-tw"

    file_name = "海盗战记 S01E01.SC.ass"
    sf = torrent_parser(file_name)
    assert sf.title == "海盗战记"
    assert sf.season == 1
    assert sf.episode == 1
    assert sf.language == "zh"

    file_name = "水星的魔女(2022) S00E19.mp4"
    bf = torrent_parser(file_name)
    assert bf.title == "水星的魔女"
    assert bf.season == 0
    assert bf.episode == 19

    file_name = "【失眠搬运组】放学后失眠的你-Kimi wa Houkago Insomnia - 06 [bilibili - 1080p AVC1 CHS-JP].mp4"
    bf = torrent_parser(file_name)
    assert bf.title == "放学后失眠的你-Kimi"
    assert bf.season == 1
    assert bf.episode == 6
