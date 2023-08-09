from module.conf import VERSION


def version_check() -> bool:
    with open("config/version.txt", "rw") as f:
        version = f.read()
        if VERSION > version:
            f.write(VERSION)
            return False
        else:
            return True
