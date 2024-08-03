import asyncio
import base64
from os.path import isfile


def url_to_str(url):
    """
    将URL编码为字符串
    """
    encoded_url = base64.urlsafe_b64encode(url.encode()).decode()
    return encoded_url

def str_to_url(encoded_str):
    """
    将编码字符串解码为URL
    """
    decoded_url = base64.urlsafe_b64decode(encoded_str.encode()).decode()
    return decoded_url

def gen_poster_path(link:str):
    return f"posters/{url_to_str(link)}"


async def save_image(link:str):

    from module.network import RequestContent

    img_hash = url_to_str(link)
    image_path = f"data/posters/{img_hash}"
    async with RequestContent() as req:
        img = await req.get_content(link)
        if img:
            with open(image_path, "wb") as f:
                f.write(img)
    return img


async def load_image(img_path:str):
    if img_path and isfile(img_path):
        with open(f"data/{img_path}", "rb") as f:
            return f.read()
    elif img_path:
        link = img_path.split("/")[-1]
        link = str_to_url(link)
        img_data = await save_image(link)
        if img_data:
            return img_data


if __name__ == "__main__":
    img_path = "posters/aHR0cHM6Ly9taWthbmFuaS5tZS9pbWFnZXMvQmFuZ3VtaS8yMDIzMDkvYTQ2ZWVhYzcuanBnP3dpZHRoP TQwMCZoZWlnaHQ9NTYwJmZvcm1hdD13ZWJw"
    asyncio.run(load_image(img_path))


