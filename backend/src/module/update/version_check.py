from module.conf import VERSION


def version_check() -> bool:
    with open("config/version.txt", "rw") as f:
        # Read last version
        versions = f.readlines()
        if VERSION[:3] > versions[-1][:3]:
            f.write(VERSION[:3] + "\n")
            return False
        else:
            return True
