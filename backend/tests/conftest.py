import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SOVEREIGN_DATABASE_URL", "sqlite://")  # in-memory

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    yield session
    session.close()


@pytest.fixture()
def seeded_db(db):
    from app.seeds.demo import seed_demo
    seed_demo(db)
    return db


@pytest.fixture()
def client(db, monkeypatch):
    """TestClient over the real app wired to the in-memory DB, with the
    Indian roster + synthetic demo data seeded (mirrors production startup)."""
    from fastapi.testclient import TestClient

    from app import main
    from app.core import db as core_db
    from app.seeds.demo import seed_demo
    from app.seeds.roster import seed_indian_roster

    monkeypatch.setattr(core_db, "SessionLocal", lambda: db)

    def override_get_db():
        yield db

    main.app.dependency_overrides[core_db.get_db] = override_get_db
    seed_indian_roster(db)
    seed_demo(db)
    with TestClient(main.app, raise_server_exceptions=True) as c:
        yield c
    main.app.dependency_overrides.clear()
