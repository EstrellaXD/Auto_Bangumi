"""Contract tests for the release-trigger classifier used by GitHub Actions."""

import runpy
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[3] / "scripts" / "classify_release.py"
SCRIPT = runpy.run_path(str(SCRIPT_PATH))
classify_release = SCRIPT["classify_release"]
ReleaseClassificationError = SCRIPT["ReleaseClassificationError"]

NO_RELEASE = {
    "release": "0",
    "dev": "0",
    "build_test": "0",
    "version": "Test",
}


@pytest.mark.parametrize(
    ("event_name", "ref_type", "ref_name", "pr_head", "pr_title", "expected"),
    [
        ("push", "branch", "main", "", "", NO_RELEASE),
        (
            "pull_request",
            "branch",
            "42/merge",
            "Doc-update",
            "Doc update",
            NO_RELEASE,
        ),
        (
            "pull_request",
            "branch",
            "42/merge",
            "3.4-dev",
            "Doc update",
            {**NO_RELEASE, "build_test": "1"},
        ),
        ("push", "tag", "Doc-update", "", "", NO_RELEASE),
    ],
)
def test_non_release_events_never_derive_version_from_pr_metadata(
    event_name, ref_type, ref_name, pr_head, pr_title, expected
):
    assert (
        classify_release(
            event_name=event_name,
            ref_type=ref_type,
            ref_name=ref_name,
            pr_head=pr_head,
            pr_title=pr_title,
        )
        == expected
    )


def test_stable_semver_tag_on_main_is_a_stable_release():
    assert classify_release(
        event_name="push",
        ref_type="tag",
        ref_name="3.3.4",
        stable_tag_on_main=True,
    ) == {
        "release": "1",
        "dev": "0",
        "build_test": "0",
        "version": "3.3.4",
    }


def test_stable_semver_tag_off_main_is_rejected():
    with pytest.raises(
        ReleaseClassificationError,
        match="does not point to a commit on main",
    ):
        classify_release(
            event_name="push",
            ref_type="tag",
            ref_name="3.3.4",
            stable_tag_on_main=False,
        )


def test_beta_semver_tag_is_a_dev_release():
    assert classify_release(
        event_name="push",
        ref_type="tag",
        ref_name="3.4.0-beta.1",
    ) == {
        "release": "1",
        "dev": "1",
        "build_test": "0",
        "version": "3.4.0-beta.1",
    }


@pytest.mark.parametrize("pr_title", ["Doc update", "3.3.4", "3.4.0-beta.1"])
def test_pr_title_is_never_a_version_source(pr_title):
    result = classify_release(
        event_name="pull_request",
        ref_type="branch",
        ref_name="1074/merge",
        pr_head="docs/update",
        pr_title=pr_title,
    )

    assert result["version"] == "Test"
    assert result["release"] == "0"


def test_release_job_marks_dev_tags_prerelease_and_attaches_plugin_assets():
    """beta 与稳定版共用 release 作业；dev=1 即预发布，两者都带 SDK 轮子与 skill。"""
    workflow = SCRIPT_PATH.parents[1] / ".github" / "workflows" / "build.yml"
    source = workflow.read_text(encoding="utf-8")
    release = source[source.index("\n  release:\n") : source.index("\n  telegram:\n")]
    assert "needs.version-info.outputs.release == 1" in release
    assert "pre_release=true" in release
    assert "sdk-dist/*.whl" in release
    assert "autobangumi-plugin-skill-" in release
    assert (
        SCRIPT_PATH.parents[1] / "skills" / "autobangumi-plugin" / "SKILL.md"
    ).is_file()


def test_update_bundle_carries_sdk_and_requires_4x_image():
    """4.x bundle 带 ab_sdk 与新依赖；3.3 镜像在 beta 通道会选中它，
    只能靠 min_image_version 拒绝（3.3 的 boot_overlay 不会替换 ab_sdk）。"""
    workflow = SCRIPT_PATH.parents[1] / ".github" / "workflows" / "build.yml"
    source = workflow.read_text(encoding="utf-8")
    step = source[
        source.index("- name: Build update bundle") : source.index(
            "- name: Sign update bundle"
        )
    ]
    assert 'MIN_IMAGE_VERSION="4.0.0-beta.1"' in step
    assert 'cp -r backend/src/ab_sdk "$STAGE/backend/src/ab_sdk"' in step
