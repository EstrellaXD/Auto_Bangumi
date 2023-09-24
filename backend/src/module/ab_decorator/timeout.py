import signal


def timeout(seconds):
    def decorator(func):
        def handler(signum, frame):
            raise TimeoutError("Function timed out.")

        def wrapper(*args, **kwargs):
            # 设置信号处理程序，当超时时触发TimeoutError异常
            signal.signal(signal.SIGALRM, handler)
            signal.alarm(seconds)  # 设置alarm定时器

            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)  # 取消alarm定时器

            return result

        return wrapper

    return decorator
