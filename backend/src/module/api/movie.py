from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from module.database import Database, get_db
from module.models import APIResponse, Movie
from module.models.movie import MovieUpdate
from module.security.api import get_current_user

router = APIRouter(prefix="/movie", tags=["movie"])


@router.get(
    "/get/all",
    response_model=list[Movie],
    dependencies=[Depends(get_current_user)],
)
async def get_all_movies(db: Database = Depends(get_db)):
    return await db.movie.search_all()


@router.get(
    "/get/{movie_id}",
    response_model=Movie,
    dependencies=[Depends(get_current_user)],
)
async def get_movie(movie_id: int, db: Database = Depends(get_db)):
    movie = await db.movie.search_id(movie_id)
    if not movie:
        return JSONResponse(
            status_code=404,
            content={
                "msg_en": f"Movie {movie_id} not found.",
                "msg_zh": f"未找到剧场版 {movie_id}。",
            },
        )
    return movie


@router.patch(
    "/update/{movie_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def update_movie(
    movie_id: int,
    data: MovieUpdate,
    db: Database = Depends(get_db),
):
    success = await db.movie.update(data, _id=movie_id)
    if success:
        return JSONResponse(
            status_code=200,
            content={"msg_en": "Movie updated.", "msg_zh": "剧场版已更新。"},
        )
    return JSONResponse(
        status_code=404,
        content={
            "msg_en": f"Movie {movie_id} not found.",
            "msg_zh": f"未找到剧场版 {movie_id}。",
        },
    )


@router.delete(
    "/delete/{movie_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def delete_movie(movie_id: int, db: Database = Depends(get_db)):
    await db.movie.delete_one(movie_id)
    return JSONResponse(
        status_code=200,
        content={"msg_en": "Movie deleted.", "msg_zh": "剧场版已删除。"},
    )


@router.delete(
    "/disable/{movie_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def disable_movie(movie_id: int, db: Database = Depends(get_db)):
    await db.movie.disable_rule(movie_id)
    return JSONResponse(
        status_code=200,
        content={"msg_en": "Movie disabled.", "msg_zh": "剧场版已禁用。"},
    )


@router.get(
    "/enable/{movie_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def enable_movie(movie_id: int, db: Database = Depends(get_db)):
    await db.movie.enable_rule(movie_id)
    return JSONResponse(
        status_code=200,
        content={"msg_en": "Movie enabled.", "msg_zh": "剧场版已启用。"},
    )
