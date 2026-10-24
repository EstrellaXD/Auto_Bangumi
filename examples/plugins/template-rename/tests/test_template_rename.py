import pytest
from pydantic import ValidationError
from template_rename import Options, Strategy, TemplateRename

from ab_sdk.rename import RenameInput, RenameSkipped
from ab_sdk.testing import RenameStrategyContract, create_plugin


class TestStrategy(RenameStrategyContract):
    def create(self):
        plugin, _ = create_plugin(TemplateRename)
        return plugin.strategy()


def media(**kwargs) -> RenameInput:
    base = dict(
        kind="media",
        media_path="x.mkv",
        title="Sample: Zero",
        bangumi_name="Sample: Zero (2024)",
        season=1,
        episode=5,
        suffix=".mkv",
    )
    return RenameInput(**{**base, **kwargs})


@pytest.mark.parametrize(
    ("template", "f", "expected"),
    [
        (
            "{bangumi_name|sanitize} S{season|pad:2}E{episode|pad:2}",
            media(),
            "Sample Zero (2024) S01E05.mkv",
        ),
        ("{title|short:6|upper}", media(), "SAMPLE.mkv"),
        (
            "{title|sanitize}",
            media(kind="subtitle", language="zh"),
            "Sample Zero.zh.mkv",
        ),
        ("E{episode|pad:2}", media(episode=9.5), "E09.5.mkv"),
    ],
)
def test_target_name_renders_filters(template, f, expected):
    assert Strategy(template).target_name(f) == expected


@pytest.mark.parametrize("template", ["{nope}", "{title|bold}", "{episode|pad:x}"])
def test_options_invalid_template_is_rejected(template):
    with pytest.raises((ValidationError, ValueError)):
        Options(template=template)


@pytest.mark.parametrize("template", ["{title}/{episode}", "{group}"])
def test_target_name_unusable_result_skips_file(template):
    with pytest.raises(RenameSkipped):
        Strategy(template).target_name(media(title="a/b", group=None))
