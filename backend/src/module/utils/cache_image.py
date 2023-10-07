import hashlib


def save_image(img, suffix):
    img_hash = hashlib.md5(img).hexdigest()[0:8]
    image_path = f"data/posters/{img_hash}.{suffix}"
    with open(image_path, "wb") as f:
        f.write(img)
    return f"posters/{img_hash}.{suffix}"


def load_image(img_path):
    if img_path:
        with open(f"data/{img_path}", "rb") as f:
            return f.read()
    else:
        return None
