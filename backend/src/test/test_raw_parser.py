import pytest

from module.parser.analyser import raw_parser


def test_raw_parser():
    # Issue #794, RSS link: https://mikanani.me/RSS/Bangumi?bangumiId=3367&subgroupid=370
    content = "[喵萌奶茶屋&LoliHouse] 鹿乃子乃子乃子虎视眈眈 / Shikanoko Nokonoko Koshitantan\n- 01 [WebRip 1080p HEVC-10bit AAC][简繁内封字幕]"
    info = raw_parser(content)
    assert info is not None
    assert info.group == "喵萌奶茶屋&LoliHouse"
    assert info.title_zh == "鹿乃子乃子乃子虎视眈眈"
    assert info.title_en == "Shikanoko Nokonoko Koshitantan"
    assert info.resolution == "1080p"
    assert info.episode == 1
    assert info.season == 1

    # Issue #679, RSS link: https://mikanani.me/RSS/Bangumi?bangumiId=3225&subgroupid=370
    content = "[LoliHouse] 轮回七次的反派大小姐，在前敌国享受随心所欲的新婚生活\n / 7th Time Loop - 12 [WebRip 1080p HEVC-10bit AAC][简繁内封字幕][END]"
    info = raw_parser(content)
    assert info is not None
    assert info.group == "LoliHouse"
    assert info.title_zh == "轮回七次的反派大小姐，在前敌国享受随心所欲的新婚生活"
    assert info.title_en == "7th Time Loop"
    assert info.resolution == "1080p"
    assert info.episode == 12
    assert info.season == 1

    content = "【幻樱字幕组】【4月新番】【古见同学有交流障碍症 第二季 Komi-san wa, Komyushou Desu. S02】【22】【GB_MP4】【1920X1080】"
    info = raw_parser(content)
    assert info is not None
    assert info.title_en == "Komi-san wa, Komyushou Desu."
    assert info.resolution == "1920X1080"
    assert info.episode == 22
    assert info.season == 2

    content = "[百冬练习组&LoliHouse] BanG Dream! 少女乐团派对！☆PICO FEVER！ / Garupa Pico: Fever! - 26 [WebRip 1080p HEVC-10bit AAC][简繁内封字幕][END] [101.69 MB]"
    info = raw_parser(content)
    assert info is not None
    assert info.group == "百冬练习组&LoliHouse"
    assert info.title_zh == "BanG Dream! 少女乐团派对！☆PICO FEVER！"
    assert info.resolution == "1080p"
    assert info.episode == 26
    assert info.season == 1

    content = "【喵萌奶茶屋】★04月新番★[夏日重现/Summer Time Rendering][11][1080p][繁日双语][招募翻译]"
    info = raw_parser(content)
    assert info is not None
    assert info.group == "喵萌奶茶屋"
    assert info.title_en == "Summer Time Rendering"
    assert info.resolution == "1080p"
    assert info.episode == 11
    assert info.season == 1

    content = "[Lilith-Raws] 关于我在无意间被隔壁的天使变成废柴这件事 / Otonari no Tenshi-sama - 09 [Baha][WEB-DL][1080p][AVC AAC][CHT][MP4]"
    info = raw_parser(content)
    assert info is not None
    assert info.group == "Lilith-Raws"
    assert info.title_zh == "关于我在无意间被隔壁的天使变成废柴这件事"
    assert info.title_en == "Otonari no Tenshi-sama"
    assert info.resolution == "1080p"
    assert info.episode == 9
    assert info.season == 1

    content = (
        "[梦蓝字幕组]New Doraemon 哆啦A梦新番[747][2023.02.25][AVC][1080P][GB_JP][MP4]"
    )
    info = raw_parser(content)
    assert info is not None
    assert info.group == "梦蓝字幕组"
    assert info.title_zh == "哆啦A梦新番"
    assert info.title_en == "New Doraemon"
    assert info.resolution == "1080P"
    assert info.episode == 747
    assert info.season == 1

    content = (
        "[织梦字幕组][尼尔：机械纪元 NieR Automata Ver1.1a][02集][1080P][AVC][简日双语]"
    )
    info = raw_parser(content)
    assert info is not None
    assert info.group == "织梦字幕组"
    assert info.title_zh == "尼尔：机械纪元"
    assert info.title_en == "NieR Automata Ver1.1a"
    assert info.resolution == "1080P"
    assert info.episode == 2
    assert info.season == 1

    content = "[MagicStar] 假面骑士Geats / 仮面ライダーギーツ EP33 [WEBDL] [1080p] [TTFC]【生】"
    info = raw_parser(content)
    assert info is not None
    assert info.group == "MagicStar"
    assert info.title_zh == "假面骑士Geats"
    assert info.title_jp == "仮面ライダーギーツ"
    assert info.resolution == "1080p"
    assert info.episode == 33
    assert info.season == 1

    content = "【极影字幕社】★4月新番 天国大魔境 Tengoku Daimakyou 第05话 GB 720P MP4（字幕社招人内详）"
    info = raw_parser(content)
    assert info is not None
    assert info.group == "极影字幕社"
    assert info.title_zh == "天国大魔境"
    assert info.title_en == "Tengoku Daimakyou"
    assert info.resolution == "720P"
    assert info.episode == 5
    assert info.season == 1

    content = "【喵萌奶茶屋】★07月新番★[银砂糖师与黑妖精 ~ Sugar Apple Fairy Tale ~][13][1080p][简日双语][招募翻译]"
    info = raw_parser(content)
    assert info is not None
    assert info.group == "喵萌奶茶屋"
    assert info.title_zh == "银砂糖师与黑妖精"
    assert info.title_en == "~ Sugar Apple Fairy Tale ~"
    assert info.resolution == "1080p"
    assert info.episode == 13
    assert info.season == 1

    content = "[ANi]  16bit 的感动 ANOTHER LAYER - 01 [1080P][Baha][WEB-DL][AAC AVC][CHT][MP4]"
    info = raw_parser(content)
    assert info is not None
    assert info.group == "ANi"
    assert info.title_zh == "16bit 的感动 ANOTHER LAYER"
    assert info.resolution == "1080P"
    assert info.episode == 1
    assert info.season == 1

    # Chinese season number via CHINESE_NUMBER_MAP ("二" → 2)
    content = "[LoliHouse] 关于我转生变成史莱姆这档事 第二季 / Tensei shitara Slime Datta Ken 2nd Season - 01 [WebRip 1080p HEVC-10bit AAC][简繁内封字幕]"
    info = raw_parser(content)
    assert info is not None
    assert info.group == "LoliHouse"
    assert info.title_zh == "关于我转生变成史莱姆这档事"
    assert info.title_en == "Tensei shitara Slime Datta Ken 2nd Season"
    assert info.resolution == "1080p"
    assert info.episode == 1
    assert info.season == 2

    # 4K resolution (2160p) — RESOLUTION_RE covers 2160 but untested
    content = "[NC-Raws] 葬送的芙莉莲 / Sousou no Frieren - 03 [B-Global][WEB-DL][2160p][AVC AAC][Multi Sub][MKV]"
    info = raw_parser(content)
    assert info is not None
    assert info.group == "NC-Raws"
    assert info.title_zh == "葬送的芙莉莲"
    assert info.title_en == "Sousou no Frieren"
    assert info.resolution == "2160p"
    assert info.episode == 3
    assert info.season == 1

    # English "Season N" format (bracketed) — season_rule "Season \d{1,2}" branch
    content = "[LoliHouse] 狼与香辛料 [Season 2] / Spice and Wolf - 01 [WebRip 1080p HEVC-10bit AAC][简繁内封字幕]"
    info = raw_parser(content)
    assert info is not None
    assert info.group == "LoliHouse"
    assert info.title_zh == "狼与香辛料"
    assert info.title_en == "Spice and Wolf"
    assert info.resolution == "1080p"
    assert info.episode == 1
    assert info.season == 2

    # Multi-group, Chinese punctuation in title, single-letter Latin prefix in EN title
    content = "[北宇治字幕组&LoliHouse] 地。-关于地球的运动- / Chi. Chikyuu no Undou ni Tsuite - 03 [WebRip 1080p HEVC-10bit AAC ASSx2][简繁日内封字幕]"
    info = raw_parser(content)
    assert info is not None
    assert info.group == "北宇治字幕组&LoliHouse"
    assert info.title_zh == "地。-关于地球的运动-"
    assert info.title_en == "Chi. Chikyuu no Undou ni Tsuite"
    assert info.resolution == "1080p"
    assert info.episode == 3
    assert info.season == 1

    # English-only title — name_process returns title_zh=None when no CJK chars
    content = "[动漫国字幕组&LoliHouse] THE MARGINAL SERVICE - 08 [WebRip 1080p HEVC-10bit AAC][简繁内封字幕]"
    info = raw_parser(content)
    assert info is not None
    assert info.group == "动漫国字幕组&LoliHouse"
    assert info.title_en == "THE MARGINAL SERVICE"
    assert info.title_zh is None
    assert info.resolution == "1080p"
    assert info.episode == 8
    assert info.season == 1

    # Issue #990: Title starting with number — should not misparse "29" as episode
    content = (
        "[ANi] 29 岁单身中坚冒险家的日常 - 07 [1080P][Baha][WEB-DL][AAC AVC][CHT][MP4]"
    )
    info = raw_parser(content)
    assert info is not None
    assert info.group == "ANi"
    assert info.title_zh == "29 岁单身中坚冒险家的日常"
    assert info.resolution == "1080P"
    assert info.episode == 7
    assert info.season == 1


# ---------------------------------------------------------------------------
# Issue-specific regression tests
# ---------------------------------------------------------------------------


class TestIssue924SpecialPunctuation:
    """Issue #924: Title with full-width parentheses and exclamation marks."""

    def test_parse_title_with_fullwidth_parens(self):
        content = "[御坂字幕组] 男女之间存在纯友情吗？（不，不存在!!）-01 [WebRip 1080p HEVC10-bit AAC] [简繁日内封] [急招翻校轴]"
        info = raw_parser(content)
        assert info is not None
        assert info is not None
        assert info.group == "御坂字幕组"
        assert info.title_zh == "男女之间存在纯友情吗？（不，不存在!!）"
        assert info.episode == 1
        assert info.resolution == "1080p"
        assert info.sub == "简繁日内封"
        assert info.source == "WebRip"


class TestIssue910NeoQswFormat:
    """Issue #910: NEO·QSW group format with inline episode number."""

    TITLE = " [NEO·QSW]想星的阿克艾利昂 情感神话 想星のアクエリオン Aquarion: Myth of Emotions 02[WEBRIP AVC 1080P]（搜索用：想星的大天使）"

    def test_parse_neo_qsw_format(self):
        info = raw_parser(self.TITLE)
        assert info is not None
        assert info is not None
        assert info.title_zh == "想星的阿克艾利昂"
        assert info.episode == 2


class TestIssue876NoSeparator:
    """Issue #876: Episode number without dash separator.

    Note: the dash-separated variant "- 03" already works (tested in test_raw_parser).
    This tests the space-only variant "Tsuite 03" which the fallback parser handles.
    """

    TITLE = "[北宇治字幕组&LoliHouse] 地。-关于地球的运动- / Chi. Chikyuu no Undou ni Tsuite 03 [WebRip 1080p HEVC-10bit AAC ASSx2][简繁日内封字幕]"

    def test_parse_without_dash(self):
        info = raw_parser(self.TITLE)
        assert info is not None
        assert info is not None
        assert info.title_zh == "地。-关于地球的运动-"
        assert info.title_en == "Chi. Chikyuu no Undou ni Tsuite"
        assert info.episode == 3


class TestIssue819ChineseEpisodeMarker:
    """Issue #819: [Doomdos] format with 第N话 episode marker."""

    def test_parse_chinese_episode_marker(self):
        content = "[Doomdos] - 白色闪电 - 第02话 - [1080P].mp4"
        info = raw_parser(content)
        assert info is not None
        assert info is not None
        assert info.group == "Doomdos"
        assert info.episode == 2
        assert info.resolution == "1080P"
        # BUG: title_zh includes leading/trailing dashes from the separator
        assert info.title_zh == "- 白色闪电 -"


class TestIssue811ColonInTitle:
    """Issue #811: Title with colon and degree symbol in group name."""

    def test_parse_colon_in_english_title(self):
        content = "[Up to 21°C] 鬼灭之刃 柱训练篇 / Kimetsu no Yaiba: Hashira Geiko-hen - 03 (CR 1920x1080 AVC AAC MKV)"
        info = raw_parser(content)
        assert info is not None
        assert info is not None
        assert info.group == "Up to 21°C"
        assert info.title_zh == "鬼灭之刃 柱训练篇"
        assert info.title_en == "Kimetsu no Yaiba: Hashira Geiko-hen"
        assert info.episode == 3
        assert info.season == 1


class TestIssue798VTuberTitle:
    """Issue #798: Title with 'VTuber' split incorrectly by name_process."""

    def test_parse_vtuber_title(self):
        content = "[ANi] 身为 VTuber 的我因为忘记关台而成了传说 - 01 [1080P][Baha][WEB-DL][AAC AVC][CHT][MP4][379.34 MB]"
        info = raw_parser(content)
        assert info is not None
        assert info is not None
        assert info.group == "ANi"
        assert info.episode == 1
        assert info.resolution == "1080P"
        assert info.source == "Baha"
        # BUG: name_process splits on space and only keeps first Chinese word
        assert info.title_zh == "身为"
        assert info.title_en == "VTuber 的我因为忘记关台而成了传说"


class TestIssue794PreEpisodeFormat:
    """Issue #794/#800: [01Pre] episode format not recognized."""

    TITLES = [
        "[KitaujiSub] Shikanoko Nokonoko Koshitantan [01Pre][WebRip][HEVC_AAC][CHS_JP].mp4",
        "[KitaujiSub] Shikanoko Nokonoko Koshitantan [01Pre][WebRip][HEVC_AAC][CHT_JP].mp4",
    ]

    @pytest.mark.xfail(reason="[01Pre] episode format not supported by TITLE_RE")
    def test_parse_pre_episode(self):
        info = raw_parser(self.TITLES[0])
        assert info is not None
        assert info is not None
        assert info.title_en == "Shikanoko Nokonoko Koshitantan"
        assert info.episode == 1

    @pytest.mark.parametrize("title", TITLES)
    def test_returns_none(self, title):
        """Parser cannot handle [01Pre] format currently."""
        assert raw_parser(title) is None


class TestIssue766Lv2InTitle:
    """Issue #766: Title with 'Lv2' causing incorrect name split."""

    def test_parse_lv2_title(self):
        content = "[ANi]  从 Lv2 开始开外挂的前勇者候补过著悠哉异世界生活 - 04 [1080P][Baha][WEB-DL][AAC AVC][CHT][MP4]"
        info = raw_parser(content)
        assert info is not None
        assert info is not None
        assert info.group == "ANi"
        assert info.episode == 4
        assert info.resolution == "1080P"
        assert info.source == "Baha"
        # BUG: name_process splits on space, loses the "从 Lv2" prefix
        assert info.title_zh == "开始开外挂的前勇者候补过著悠哉异世界生活"


class TestIssue764WesternFormat:
    """Issue #764: Western release format without group brackets."""

    def test_parse_western_format(self):
        content = "Girls Band Cry S01E05 VOSTFR 1080p WEB x264 AAC -Tsundere-Raws (ADN)"
        info = raw_parser(content)
        assert info is not None
        assert info is not None
        assert info.episode == 5
        assert info.season == 1
        assert info.resolution == "1080p"
        # No brackets → group detection fails
        assert info.group == ""
        # After the #1025 fix, prefix_process no longer destroys titles without
        # a [group] prefix, so the English title is now extracted correctly.
        assert info.title_en == "Girls Band Cry"
        assert info.title_zh is None


class TestIssue986AtlasFormat:
    """Issue #986: Atlas subtitle group bracket-delimited format."""

    TITLES = [
        "[阿特拉斯字幕组·雪原市出差所][命运-奇异赝品_Fate／strange Fake][04_半神们的卡农曲][简繁日内封PGS][日语配音版_Japanese Dub][Web-DL Remux][1080p AVC AAC]",
        "[阿特拉斯字幕组·雪原市出差所][命运-奇异赝品_Fate／strange Fake][07_神自黄昏归来][简繁日内封PGS][日语配音版_Japanese Dub][Web-DL Remux][1080p AVC AAC]",
    ]

    @pytest.mark.xfail(
        reason="Atlas bracket-delimited format not supported by TITLE_RE"
    )
    def test_parse_atlas_format(self):
        info = raw_parser(self.TITLES[0])
        assert info is not None
        assert info is not None
        assert info.title_zh == "命运-奇异赝品"
        assert info.episode == 4

    @pytest.mark.parametrize("title", TITLES)
    def test_returns_none(self, title):
        """Parser cannot handle Atlas format currently."""
        assert raw_parser(title) is None


class TestIssue773CompoundEpisode:
    """Issue #773: Compound episode number [02(57)] not recognized."""

    TITLE = "【豌豆字幕组&风之圣殿字幕组】★04月新番[鬼灭之刃 柱训练篇 / Kimetsu_no_Yaiba-Hashira_Geiko_Hen][02(57)][简体][1080P][MP4]"

    def test_parse_compound_episode(self):
        info = raw_parser(self.TITLE)
        assert info is not None
        assert info is not None
        assert info.title_zh == "鬼灭之刃 柱训练篇"
        assert info.episode == 2


class TestMovieAndSpecialParsing:
    """Movies / OVA / OAD / SP / Special titles have no regular episode number,
    so TITLE_RE and the fallback patterns both fail. Previously raw_parser
    returned None for these and the resource was silently dropped; it now
    recognizes the type tokens and returns a typed Episode instead."""

    def test_parse_movie_with_juchangban_token(self):
        content = (
            "[Lilith-Raws] 天气之子 / Tenki no Ko 剧场版 [Baha][WEB-DL][1080p][MP4]"
        )
        info = raw_parser(content)
        assert info is not None
        assert info.episode_type == "movie"
        assert info.title_zh == "天气之子"
        assert info.title_en == "Tenki no Ko"
        assert info.season == 1

    def test_parse_movie_with_movie_token(self):
        content = "[SubGroup] 某剧场作品 Movie [1080p][MP4]"
        info = raw_parser(content)
        assert info is not None
        assert info.episode_type == "movie"

    def test_parse_ova_sets_special_type_and_season_zero(self):
        content = "[LoliHouse] 鬼灭之刃 / Kimetsu no Yaiba OVA01 [WebRip 1080p HEVC-10bit AAC]"
        info = raw_parser(content)
        assert info is not None
        assert info.episode_type == "special"
        assert info.season == 0
        assert info.episode == 1
        assert info.title_zh == "鬼灭之刃"
        assert info.title_en == "Kimetsu no Yaiba"

    def test_parse_sp_token_extracts_episode_number(self):
        content = "[SubGroup] 某动画 SP02 [1080p]"
        info = raw_parser(content)
        assert info is not None
        assert info.episode_type == "special"
        assert info.season == 0
        assert info.episode == 2

    def test_parse_special_token_without_digit_defaults_episode_zero(self):
        content = "[SubGroup] 某动画 Special [1080p]"
        info = raw_parser(content)
        assert info is not None
        assert info.episode_type == "special"
        assert info.episode == 0

    def test_non_matching_title_without_tokens_still_returns_none(self):
        """A genuinely unparseable title with no movie/special tokens must
        still return None so it is not silently accepted as garbage."""
        assert raw_parser("Random Non Matching Title No Digits At All") is None

    def test_regular_episode_has_episode_type_episode(self):
        """Normal episodic titles are unaffected: episode_type defaults to
        'episode'."""
        content = "[LoliHouse] 关于我转生变成史莱姆这档事 第二季 / Tensei shitara Slime Datta Ken 2nd Season - 01 [WebRip 1080p HEVC-10bit AAC][简繁内封字幕]"
        info = raw_parser(content)
        assert info is not None
        assert info.episode_type == "episode"


class TestIssue805TitleWithCht:
    """Issue #805: Traditional Chinese title parses correctly."""

    def test_parse_cht_title(self):
        content = "[ANi] 不時輕聲地以俄語遮羞的鄰座艾莉同學 - 02 [1080P][Baha][WEB-DL][AAC AVC][CHT].mp4"
        info = raw_parser(content)
        assert info is not None
        assert info is not None
        assert info.group == "ANi"
        assert info.title_zh == "不時輕聲地以俄語遮羞的鄰座艾莉同學"
        assert info.episode == 2
        assert info.resolution == "1080P"
        assert info.source == "Baha"
        assert info.sub == "CHT"


class TestIssue1025NoGroupPrefix:
    """Issue #1025: Titles without a [group] prefix must still parse.

    prefix_process was calling re.sub(f".{group}.", "", raw) even when
    group was empty, which reduced the pattern to `..` and deleted every
    pair of characters, leaving a stub like `1` that name_process couldn't
    split into en/zh/jp.
    """

    def test_mixed_cjk_and_en_without_group(self):
        content = (
            "冰之城墙「氷の城壁」The Ramparts of Ice S01E02 1080p 日英双语-多国字幕"
        )
        info = raw_parser(content)
        assert info is not None
        assert info is not None
        assert info.episode == 2
        assert info.season == 1
        # Before the fix all three title fields were None and title_parser
        # raised "Cannot extract title_raw". At least one must now be set.
        assert any([info.title_en, info.title_zh, info.title_jp])
