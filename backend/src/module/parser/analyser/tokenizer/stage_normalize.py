from .keywords import FILE_EXTENSIONS


def normalize(raw: str) -> str:
    s = raw.strip().replace("\n", " ")
    s = s.replace("【", "[").replace("】", "]")
    # Note: full-width ／ (\uff0f) is NOT normalized to /
    # It appears in CJK titles (e.g. Fate／strange Fake) and should be preserved
    s = FILE_EXTENSIONS.sub("", s)
    return s
