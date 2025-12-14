import os
from pathlib import Path

from sqlmodel import create_engine

DATA_PATH = "sqlite:///data/data.db"
# 创建 data 目录
os.makedirs("data", exist_ok=True)
POSTERS_PATH = Path("data/posters")
# 创建 posters 目录
POSTERS_PATH.mkdir(parents=True, exist_ok=True)

engine = create_engine(DATA_PATH)


# db_session = Session(engine)
