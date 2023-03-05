from module.parser.analyser import RawParser


def test_raw_parser():
    parser = RawParser()
    content = "【幻樱字幕组】【4月新番】【古见同学有交流障碍症 第二季 Komi-san wa, Komyushou Desu. S02】【22】【GB_MP4】【1920X1080】"
    info = parser.analyse(content)
    assert info.title_en == "Komi-san wa, Komyushou Desu."
    assert info.resolution == "1920X1080"
    assert info.episode == 22
    assert info.season == 2

    content = "[百冬练习组&LoliHouse] BanG Dream! 少女乐团派对！☆PICO FEVER！ / Garupa Pico: Fever! - 26 [WebRip 1080p HEVC-10bit AAC][简繁内封字幕][END] [101.69 MB]"
    info = parser.analyse(content)
    assert info.group == "百冬练习组&LoliHouse"
    assert info.title_zh == "BanG Dream! 少女乐团派对！☆PICO FEVER！"
    assert info.resolution == "1080p"
    assert info.episode == 26
    assert info.season == 1

    content = "【喵萌奶茶屋】★04月新番★[夏日重现/Summer Time Rendering][11][1080p][繁日双语][招募翻译]"
    info = parser.analyse(content)
    assert info.group == "喵萌奶茶屋"
    assert info.title_en == "Summer Time Rendering"
    assert info.resolution == "1080p"
    assert info.episode == 11
    assert info.season == 1

    content = "[Lilith-Raws] 关于我在无意间被隔壁的天使变成废柴这件事 / Otonari no Tenshi-sama - 09 [Baha][WEB-DL][1080p][AVC AAC][CHT][MP4]"
    info = parser.analyse(content)
    assert info.group == "Lilith-Raws"
    assert info.title_zh == "关于我在无意间被隔壁的天使变成废柴这件事"
    assert info.title_en == "Otonari no Tenshi-sama"
    assert info.resolution == "1080p"
    assert info.episode == 9
    assert info.season == 1
