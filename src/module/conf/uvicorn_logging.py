logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "loggers": {
        "uvicorn.error": {
            "level": "INFO",
            "handlers": ["default"],
            "propagate": True,
        },
        "uvicorn.asgi": {  # 更改 "uvicorn.access" 为 "uvicorn.asgi"
            "level": "INFO",
            "handlers": ["access"],
            "propagate": True,
        },
    },
    "handlers": {
        "default": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "default",
        },
        "access": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "access",
        },
    },
    "formatters": {
        "default": {
            "format": "[%(asctime)s] %(levelname)-8s  %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "access": {
            "format": "[%(asctime)s] %(levelname)s: %(client_addr)s - \"%(request_line)s\" %(status_code)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
}