import logging

from module.rss import RSSEngine
from module.conf import settings

logger = logging.getLogger(__name__)


def start_up(first_run):
    with RSSEngine() as engine:
        engine.create_table()
        engine.user.add_default_user()
        if not first_run:
            main_rss = engine.rss.search_id(1)
            if not main_rss:
                engine.add_rss(settings.rss_link, name="Mikan RSS", combine=True)
            elif main_rss.url != settings.rss_link:
                main_rss.url = settings.rss_link
                engine.rss.update(main_rss)


if __name__ == "__main__":
    start_up(False)
