import semver

from module.conf import VERSION, VERSION_PATH


def version_check() -> tuple[bool, int | None]:
    """Check if version has changed.

    Returns:
        A tuple of (is_same_version, last_minor_version).
        last_minor_version is None if no upgrade is needed.
    """
    if VERSION == "DEV_VERSION":
        return True, None
    if VERSION == "local":
        return True, None
    if not VERSION_PATH.exists():
        with open(VERSION_PATH, "w") as f:
            f.write(VERSION + "\n")
        return False, None
    else:
        with open(VERSION_PATH, "r+") as f:
            # Read last version
            versions = f.readlines()
            last_version = versions[-1].strip()
            last_ver = semver.VersionInfo.parse(last_version)
            now_ver = semver.VersionInfo.parse(VERSION)
            if now_ver.minor == last_ver.minor:
                return True, None
            else:
                if now_ver.minor > last_ver.minor:
                    f.write(VERSION + "\n")
                    return False, last_ver.minor
                else:
                    return True, None
