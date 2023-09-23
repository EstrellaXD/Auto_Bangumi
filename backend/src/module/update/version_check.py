import semver

from module.conf import VERSION, VERSION_PATH


def version_check() -> bool:
    if VERSION == "DEV_VERSION":
        return True
    if not VERSION_PATH.exists():
        with open(VERSION_PATH, "w") as f:
            f.write(VERSION + "\n")
        return False
    else:
        with open(VERSION_PATH, "r+") as f:
            # Read last version
            versions = f.readlines()
            last_version = versions[-1]
            last_ver = semver.VersionInfo.parse(last_version)
            now_ver = semver.VersionInfo.parse(VERSION)
            if now_ver.minor == last_ver.minor:
                return True
            else:
                if now_ver.minor > last_ver.minor:
                    f.write(VERSION + "\n")
                    return False
                else:
                    return True
