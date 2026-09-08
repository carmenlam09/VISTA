import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models.audit  # noqa: F401 — registers tables on Base.metadata
import app.models.vendor  # noqa: F401
from app.db.base import Base


@pytest.fixture()
def db_session(tmp_path):
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(bind=engine)
    session = session_local()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
