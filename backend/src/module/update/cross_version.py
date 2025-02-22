from module.conf import VERSION, VERSION_PATH
from module.database import Database


async def from_30_to_31():
    # 不处理 3.1.18 之前的版本数据了
    if VERSION == "DEV_VERSION":
        return True
    if VERSION == "local":
        return True
    with Database() as db:
        bangumis = db.bangumi.search_all()
        for bangumi in bangumis:
            # old format = "posters/eed922ba.jpg"
            if bangumi.poster_link and "\." in bangumi.poster_link:
                bangumi.poster_link = None
            # old format = "https://www.baidu.com/posters/eed922ba.jpg"
            if bangumi.poster_link and "http" in bangumi.poster_link:
                bangumi.poster_link = None
        db.bangumi.update_all(bangumis)

    # db.migrate()
    # # Update poster link
    # bangumis = db.bangumi.search_all()
    # rss_pool = []
    # for bangumi in bangumis:
    #     if bangumi.poster_link:
    #         rss_link = bangumi.rss_link.split(",")[-1]
    #         if rss_link not in rss_pool and not re.search(
    #             r"\d+.\d+.\d+.\d+", rss_link
    #         ):
    #             rss_pool.append(rss_link)
    #         root_path = parse_url(rss_link).host
    #         if "://" not in bangumi.poster_link:
    #             bangumi.poster_link = f"https://{root_path}{bangumi.poster_link}"
    # db.bangumi.update_all(bangumis)
    # for rss in rss_pool:
    #     if "mybangumi" in rss.lower():
    #         aggregate = True
    #     else:
    #         aggregate = False

    #     engine = RSSManager()
    #     await engine.add_rss(rss_link=rss, aggregate=aggregate)


# async def cache_image():
#     with Database() as db:
#         bangumis = db.bangumi.search_all()
#         for bangumi in bangumis:
#             if bangumi.poster_link:
#                 # Hash local path
#                 bangumi.poster_link = gen_poster_path(bangumi.poster_link)
#         db.bangumi.update_all(bangumis)

if __name__ == "__main__":
    from module.conf import VERSION

    print(from_30_to_31())
