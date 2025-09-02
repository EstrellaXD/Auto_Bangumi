import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from packaging import version

from module.conf import VERSION
from module.network.request_url import RequestURL

logger = logging.getLogger(__name__)


@dataclass
class ReleaseInfo:
    """GitHub Release信息"""

    tag_name: str
    name: str
    body: str
    html_url: str
    tarball_url: str
    zipball_url: str
    published_at: str
    prerelease: bool
    draft: bool


class ReleaseChecker:
    """GitHub Release版本检查器"""

    def __init__(self, repo_owner: str = "EstrellaXD", repo_name: str = "Auto_Bangumi"):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        # 使用GitHub的latest release重定向URL获取最新版本信息
        # https://github.com/EstrellaXD/Auto_Bangumi/releases/latest
        self.release_url = f"https://github.com/{repo_owner}/{repo_name}/releases/latest"

    async def get_all_releases(self, include_prerelease: bool = False) -> list[ReleaseInfo]:
        """获取所有发布版本信息

        Args:
            include_prerelease: 是否包含预发布版本

        Returns:
            list[ReleaseInfo]: 所有发布版本信息列表，按时间倒序
        """
        try:
            async with RequestURL() as client:
                client.header["User-Agent"] = "Auto_Bangumi/3.2.0 (https://github.com/EstrellaXD/Auto_Bangumi)"

                # 使用releases.atom RSS feed获取版本信息
                releases_atom_url = f"https://github.com/{self.repo_owner}/{self.repo_name}/releases.atom"
                response = await client.get_url(releases_atom_url)

                # 从Atom XML内容中提取所有release信息
                atom_content = response.text

                # 使用ElementTree解析Atom XML
                root = ET.fromstring(atom_content)

                # 定义命名空间
                namespaces = {"atom": "http://www.w3.org/2005/Atom"}

                entries = root.findall(".//atom:entry", namespaces)

                releases = []
                seen_tags = set()  # 避免重复

                for entry in entries:
                    # 从每个entry中提取tag_name
                    link_elem = entry.find("atom:link[@href]", namespaces)
                    if link_elem is None:
                        continue

                    href = link_elem.get("href", "")
                    if f"/releases/tag/" not in href:
                        continue

                    tag_name = href.split("/releases/tag/")[-1]
                    if tag_name in seen_tags:
                        continue
                    seen_tags.add(tag_name)

                    # 简单过滤预发布版本（通常包含 alpha, beta, rc 等）
                    if not include_prerelease:
                        lower_tag = tag_name.lower()
                        if any(keyword in lower_tag for keyword in ["alpha", "beta", "rc", "pre", "dev"]):
                            continue

                    # 提取title
                    title_elem = entry.find("atom:title", namespaces)
                    title = (
                        title_elem.text.strip()
                        if title_elem is not None and title_elem.text
                        else f"Auto_Bangumi {tag_name}"
                    )

                    # 不获取content内容，只关注版本标签
                    body = ""

                    # 提取published时间
                    published_elem = entry.find("atom:published", namespaces)
                    published_at = (
                        published_elem.text.strip() if published_elem is not None and published_elem.text else ""
                    )

                    release_info = ReleaseInfo(
                        tag_name=tag_name,
                        name=title,
                        body=body,
                        html_url=f"https://github.com/{self.repo_owner}/{self.repo_name}/releases/tag/{tag_name}",
                        tarball_url=f"https://github.com/{self.repo_owner}/{self.repo_name}/archive/refs/tags/{tag_name}.tar.gz",
                        zipball_url=f"https://github.com/{self.repo_owner}/{self.repo_name}/archive/refs/tags/{tag_name}.zip",
                        published_at=published_at,
                        prerelease=any(
                            keyword in tag_name.lower() for keyword in ["alpha", "beta", "rc", "pre", "dev"]
                        ),
                        draft=False,
                    )
                    releases.append(release_info)

                logger.info(f"Found {len(releases)} releases from {self.repo_owner}/{self.repo_name}")
                return releases

        except Exception as e:
            logger.error(f"Failed to get all releases: {e}")
            return []

    async def check_for_update(self, include_prerelease: bool = False) -> dict:
        """检查是否有可用更新
        Args:
            include_prerelease: 是否包含预发布版本

        Returns:
            dict: 包含更新检查结果的字典
        """
        current_version = VERSION

        # 如果是开发版本，跳过更新检查
        if current_version in ["DEV_VERSION", "local"]:
            return {
                "current_version": current_version,
                "latest_version": None,
                "has_update": False,
                "is_dev_version": True,
                "message": "Development version, skipping update check",
            }

        # 获取所有releases，已经过滤了预发布版本
        all_releases = await self.get_all_releases(include_prerelease=include_prerelease)

        if not all_releases:
            return {
                "current_version": current_version,
                "latest_version": None,
                "has_update": False,
                "error": "Failed to fetch release information",
            }

        try:
            current_ver = version.parse(current_version)

            # 第一个release就是最新版本（已排序）
            latest_release = all_releases[0]
            latest_ver = version.parse(latest_release.tag_name.lstrip("v"))

            has_update = latest_ver > current_ver

            return {
                "current_version": current_version,
                "latest_version": latest_release.tag_name,
                "has_update": has_update,
                "release_info": {
                    "name": latest_release.name,
                    "html_url": latest_release.html_url,
                    "published_at": latest_release.published_at,
                    "prerelease": latest_release.prerelease,
                },
            }

        except Exception as e:
            logger.error(f"Failed to compare versions: {e}")
            return {
                "current_version": current_version,
                "latest_version": all_releases[0].tag_name if all_releases else None,
                "has_update": False,
                "error": f"Version comparison failed: {str(e)}",
            }
