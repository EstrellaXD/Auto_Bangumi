import base64



def url_to_str(url):
    """
    将URL编码为字符串
    """
    encoded_url = base64.urlsafe_b64encode(url.encode()).decode()
    return encoded_url


def str_to_url(encoded_str: str) -> str:
    """
    将编码字符串解码为URL
    """
    try:
        decoded_url = base64.urlsafe_b64decode(encoded_str.encode()).decode()
        return decoded_url
    except Exception:
        # 如果不是有效的base64，直接返回原字符串
        return encoded_str


def gen_poster_path(link: str):
    # 这是给 parser 用的, 对 url 进行编码,返回即可
    return f"posters/{url_to_str(link)}"
