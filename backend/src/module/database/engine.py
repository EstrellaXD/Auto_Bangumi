from sqlmodel import create_engine, Session


engine = create_engine("sqlite:///data/data.db")

db_session = Session(engine)