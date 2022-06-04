from conf import settings

bool_group = [
    settings.enable_group_tag,
    settings.get_rule_debug,
    settings.debug_mode,
    settings.enable_eps_complete,
    settings.season_one_tag
]


def init_switch():
    if settings.sleep_time is str:
        settings.sleep_time = float(settings.sleep_time)
    for switch in bool_group:
        if switch is str:
            switch = switch.lower() in ("true", "t", "i")


if __name__ == "__main__":
    settings.init()
    settings.sleep_time = float(settings.sleep_time)
    print(type(settings.sleep_time))