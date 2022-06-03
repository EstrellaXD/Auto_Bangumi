from dataclasses import dataclass


@dataclass
class Episode:
    @dataclass
    class TitleInfo:
        def __init__(self) -> None:
            self.raw: str = None
            self.name: str = None

    @dataclass
    class SeasonInfo:
        def __init__(self) -> None:
            self.raw: str = None
            self.number: int = None

    @dataclass
    class EpisodeInfo:
        def __init__(self) -> None:
            self.raw: str = None
            self.number: int = None

    @property
    def title(self) -> str:
        return self.title_info.name

    @title.setter
    def title(self, title: str):
        self.title_info.name = title

    def __init__(self) -> None:
        self.group: str = None
        self.title_info = Episode.TitleInfo()
        self.season_info = Episode.SeasonInfo()
        self.number_info = Episode.EpisodeInfo()
        self.format: str = None
        self.subtitle: str = None
