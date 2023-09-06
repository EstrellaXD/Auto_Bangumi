

from module.conf import VERSION, VERSION_PATH


def version_check() -> bool:
    if not VERSION_PATH.exists():
        with open(VERSION_PATH, "w") as f:
            f.write(VERSION + "\n")
        return False
    else:
        with open(VERSION_PATH, "r+") as f:
            # Read last version
            versions = f.readlines()
            last_version = versions[-1]
            if VERSION == last_version:
                return True
            else:
                if VERSION[:3] > versions[-1][:3]:
                    f.write(VERSION[:3] + "\n")
                    return False
                else:
                    return True
