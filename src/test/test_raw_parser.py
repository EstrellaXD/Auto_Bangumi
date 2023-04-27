from module.parser.analyser import raw_parser


def test_raw_parser():
    content = "【幻樱字幕组】【4月新番】【古见同学有交流障碍症 第二季 Komi-san wa, Komyushou Desu. S02】【22】【GB_MP4】【1920X1080】"
    info = raw_parser(content)
    assert info.title_en == "Komi-san wa, Komyushou Desu."
    assert info.resolution == "1920X1080"
    assert info.episode == 22
    assert info.season == 2

    content = "[百冬练习组&LoliHouse] BanG Dream! 少女乐团派对！☆PICO FEVER！ / Garupa Pico: Fever! - 26 [WebRip 1080p HEVC-10bit AAC][简繁内封字幕][END] [101.69 MB]"
    info = raw_parser(content)
    assert info.group == "百冬练习组&LoliHouse"
    assert info.title_zh == "BanG Dream! 少女乐团派对！☆PICO FEVER！"
    assert info.resolution == "1080p"
    assert info.episode == 26
    assert info.season == 1

    content = "【喵萌奶茶屋】★04月新番★[夏日重现/Summer Time Rendering][11][1080p][繁日双语][招募翻译]"
    info = raw_parser(content)
    assert info.group == "喵萌奶茶屋"
    assert info.title_en == "Summer Time Rendering"
    assert info.resolution == "1080p"
    assert info.episode == 11
    assert info.season == 1

    content = "[Lilith-Raws] 关于我在无意间被隔壁的天使变成废柴这件事 / Otonari no Tenshi-sama - 09 [Baha][WEB-DL][1080p][AVC AAC][CHT][MP4]"
    info = raw_parser(content)
    assert info.group == "Lilith-Raws"
    assert info.title_zh == "关于我在无意间被隔壁的天使变成废柴这件事"
    assert info.title_en == "Otonari no Tenshi-sama"
    assert info.resolution == "1080p"
    assert info.episode == 9
    assert info.season == 1

    content = "[梦蓝字幕组]New Doraemon 哆啦A梦新番[747][2023.02.25][AVC][1080P][GB_JP][MP4]"
    info = raw_parser(content)
    assert info.group == "梦蓝字幕组"
    assert info.title_zh == "哆啦A梦新番"
    assert info.title_en == "New Doraemon"
    assert info.resolution == "1080P"
    assert info.episode == 747
    assert info.season == 1

    content = "[织梦字幕组][尼尔：机械纪元 NieR Automata Ver1.1a][02集][1080P][AVC][简日双语]"
    info = raw_parser(content)
    assert info.group == "织梦字幕组"
    assert info.title_zh == "尼尔：机械纪元 NieR Automata Ver1.1a"
    assert info.resolution == "1080P"
    assert info.episode == 2
    assert info.season == 1
