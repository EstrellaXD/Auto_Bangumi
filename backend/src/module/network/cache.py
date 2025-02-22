from os.path import isfile
from pathlib import Path

from module.utils import str_to_url, url_to_str

from .request_contents import RequestContent


async def save_image(link: str):

    img_hash = url_to_str(link)
    image_path = Path("data/posters") / img_hash
    async with RequestContent() as req:
        img = await req.get_content(link)
        if img:
            with open(image_path, "wb") as f:
                f.write(img)
    return img


async def load_image(img_path: str):
    image_path = Path("data") / img_path
    if img_path and isfile(image_path):
        with open(image_path, "rb") as f:
            return f.read()
    elif img_path:
        link = img_path.split("/")[-1]
        link = str_to_url(link)
        img_data = await save_image(link)
        if img_data:
            return img_data
