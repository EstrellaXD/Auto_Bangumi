import base64

#TODO: 移动到 network 模块下, 这里要用到 setting.proxy, 但是这里用到 network 会导致循环引用

def url_to_str(url):
    """
    将URL编码为字符串
    """
    encoded_url = base64.urlsafe_b64encode(url.encode()).decode()
    return encoded_url


def str_to_url(encoded_str:str)->str:
    """
    将编码字符串解码为URL
    """
    decoded_url = base64.urlsafe_b64decode(encoded_str.encode()).decode()
    return decoded_url


def gen_poster_path(link: str):
    # 这是给 parser 用的, 对 url 进行编码,返回即可
    return f"posters/{url_to_str(link)}"


