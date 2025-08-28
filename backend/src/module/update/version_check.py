from packaging import version

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
            last_version = versions[-1].strip()
            try:
                last_ver = version.parse(last_version)
                now_ver = version.parse(VERSION)

                # 比较minor版本号
                if now_ver.release[:2] == last_ver.release[:2]:  # major.minor相同
                    return True
                else:
                    # check 3.1.1 <= version <= 3.1.18
                    min_ver = version.parse("3.1.1")
                    max_ver = version.parse("3.1.18")
                    if min_ver <= last_ver <= max_ver:
                        f.write(VERSION + "\n")
                        return False
                    return True
            except Exception:
                # 如果版本解析失败，写入新版本并返回False
                f.write(VERSION + "\n")
                return False

                # if now_ver.minor > last_ver.minor:
                #     f.write(VERSION + "\n")
                #     return False
                # else:
                #     return True


if __name__ == "__main__":
    print(version_check())
