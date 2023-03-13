from dataclasses import dataclass


@dataclass
class MatchRule:
    keyword: str
    filter: list
    rss_link: str


class GroupFilter:
    name: str
    filter: list

