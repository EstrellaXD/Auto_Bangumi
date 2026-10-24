"""密码哈希：bcrypt，兼容 passlib 时代的 72 字节截断语义。"""

import bcrypt


def _truncate_password(password: str) -> bytes:
    # bcrypt 只使用前 72 字节；passlib 时代会静默截断，bcrypt 5.x 则对超长输入
    # 抛 ValueError。这里显式截断以保持 passlib 兼容语义：升级前用超长密码
    # （UTF-8 下中文很容易超过 72 字节）注册的用户仍可用原密码登录，设置
    # 超长新密码也不会报错。
    return password.encode("utf-8")[:72]


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        _truncate_password(plain_password), hashed_password.encode("utf-8")
    )


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(_truncate_password(password), bcrypt.gensalt()).decode("utf-8")
