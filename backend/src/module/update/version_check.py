import semver

from module.conf import VERSION, VERSION_PATH


def version_check() -> bool:
    if VERSION == "DEV_VERSION":
        return True
    if VERSION == "local":
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
                # check 3.1.1 < version < 3.1.18
                if last_version >= semver.VersionInfo.parse(
                    "3.1.1"
                ) and last_version <= semver.VersionInfo.parse("3.1.18"):
                    f.write(VERSION + "\n")
                    return False
                return True

                # if now_ver.minor > last_ver.minor:
                #     f.write(VERSION + "\n")
                #     return False
                # else:
                #     return True


if __name__ == "__main__":
    print(version_check())
