import logging
import re
import time
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import and_, false, select

from module.models.movie import Movie, MovieUpdate

logger = logging.getLogger(__name__)

# Module-level TTL cache for search_all results
_movie_cache: list[Movie] | None = None
_movie_cache_time: float = 0
_MOVIE_CACHE_TTL: float = 300.0


def _invalidate_movie_cache():
    global _movie_cache, _movie_cache_time
    _movie_cache = None
    _movie_cache_time = 0


class MovieDatabase:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _is_duplicate(self, data: Movie) -> bool:
        statement = select(Movie).where(
            and_(
                Movie.title_raw == data.title_raw,
                Movie.group_name == data.group_name,
            )
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def add(self, data: Movie) -> bool:
        if await self._is_duplicate(data):
            logger.debug(
                "Skipping duplicate movie: %s (%s)",
                data.official_title,
                data.group_name,
            )
            return False
        self.session.add(data)
        await self.session.commit()
        _invalidate_movie_cache()
        logger.debug("Insert movie %s into database.", data.official_title)
        return True

    async def search_all(self) -> list[Movie]:
        global _movie_cache, _movie_cache_time
        now = time.time()
        if _movie_cache is not None and (now - _movie_cache_time) < _MOVIE_CACHE_TTL:
            return _movie_cache
        statement = select(Movie)
        result = await self.session.execute(statement)
        movies = list(result.scalars().all())
        for m in movies:
            self.session.expunge(m)
        _movie_cache = movies
        _movie_cache_time = now
        return _movie_cache

    async def search_id(self, _id: int) -> Optional[Movie]:
        statement = select(Movie).where(Movie.id == _id)
        result = await self.session.execute(statement)
        movie = result.scalar_one_or_none()
        if movie is None:
            logger.warning(f"Cannot find movie id: {_id}.")
            return None
        return movie

    async def update(self, data: Movie | MovieUpdate, _id: int | None = None) -> bool:
        if _id and isinstance(data, MovieUpdate):
            db_data = await self.session.get(Movie, _id)
        elif isinstance(data, Movie):
            db_data = await self.session.get(Movie, data.id)
        else:
            return False
        if not db_data:
            return False
        movie_data = data.model_dump(exclude_unset=True)
        for key, value in movie_data.items():
            setattr(db_data, key, value)
        self.session.add(db_data)
        await self.session.commit()
        _invalidate_movie_cache()
        logger.debug("Update movie %s", data.official_title)
        return True

    async def delete_one(self, _id: int):
        statement = select(Movie).where(Movie.id == _id)
        result = await self.session.execute(statement)
        movie = result.scalar_one_or_none()
        if movie:
            await self.session.delete(movie)
            await self.session.commit()
            _invalidate_movie_cache()
            logger.debug("Delete movie id: %s.", _id)

    async def disable_rule(self, _id: int):
        statement = select(Movie).where(Movie.id == _id)
        result = await self.session.execute(statement)
        movie = result.scalar_one_or_none()
        if movie:
            movie.deleted = True
            self.session.add(movie)
            await self.session.commit()
            _invalidate_movie_cache()
            logger.debug("Disable movie %s.", movie.title_raw)

    async def enable_rule(self, _id: int):
        statement = select(Movie).where(Movie.id == _id)
        result = await self.session.execute(statement)
        movie = result.scalar_one_or_none()
        if movie:
            movie.deleted = False
            self.session.add(movie)
            await self.session.commit()
            _invalidate_movie_cache()
            logger.debug("Enable movie %s.", movie.title_raw)

    async def match_list(self, torrent_list: list, rss_link: str) -> list:
        # Lazy import avoids a database/parser import cycle during startup.
        from module.parser.analyser.tokenizer import MediaType, parse_release_title

        match_datas = await self.search_all()
        if not match_datas:
            return torrent_list

        title_index: dict[str, Movie] = {}
        for m in match_datas:
            if m.title_raw:
                title_index[m.title_raw] = m

        if not title_index:
            return torrent_list

        sorted_titles = sorted(title_index.keys(), key=len, reverse=True)
        pattern = "|".join(re.escape(title) for title in sorted_titles)
        title_regex = re.compile(pattern)

        unmatched = []
        rss_updated = set()
        for torrent in torrent_list:
            match = title_regex.search(torrent.name)
            release = parse_release_title(torrent.name)
            if match and release is not None and release.media_type is MediaType.MOVIE:
                matched_title = match.group(0)
                match_data = title_index[matched_title]
                if (
                    match_data.rss_link
                    and rss_link not in match_data.rss_link
                    and match_data.title_raw not in rss_updated
                ):
                    match_data = await self.session.merge(match_data)
                    match_data.rss_link = f"{match_data.rss_link},{rss_link}"
                    match_data.added = False
                    rss_updated.add(match_data.title_raw)
            else:
                unmatched.append(torrent)
        if rss_updated:
            await self.session.commit()
            _invalidate_movie_cache()
        return unmatched

    async def not_added(self) -> list[Movie]:
        conditions = select(Movie).where(
            Movie.added == false(),
        )
        result = await self.session.execute(conditions)
        return list(result.scalars().all())
