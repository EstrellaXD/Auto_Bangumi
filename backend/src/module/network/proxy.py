from module.conf import settings


@property
def set_proxy():
    auth = (
        f"{settings.proxy.username}:{settings.proxy.password}@"
        if settings.proxy.username
        else ""
    )
    if "http" in settings.proxy.type:
        proxy = (
            f"{settings.proxy.type}://{auth}{settings.proxy.host}:{settings.proxy.port}"
        )
    elif settings.proxy.type == "socks5":
        proxy = f"socks5://{auth}{settings.proxy.host}:{settings.proxy.port}"
    else:
        proxy = None
        logger.error(f"[Network] Unsupported proxy type: {settings.proxy.type}")
    return proxy
