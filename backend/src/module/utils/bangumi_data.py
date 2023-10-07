import logging

logger = logging.getLogger(__name__)


def get_poster(title: str) -> str:
    # avoid cyclic import
    from module.database import Database

    with Database() as db:
        poster = db.bangumi.match_poster(title)
        if not poster:
            logger.warning(f"Can't find poster for {title}")
            return ""
        return poster
