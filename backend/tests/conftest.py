import os

# precisa vir ANTES de importar o app, para ele não tentar conectar no Postgres
os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app

engine_teste = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SessionTeste = sessionmaker(bind=engine_teste, autoflush=False)


@pytest.fixture()
def db():
    """banco novo e vazio para cada teste (os ids recomeçam do 1)"""
    Base.metadata.create_all(bind=engine_teste)
    session = SessionTeste()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine_teste)


@pytest.fixture()
def client(db):
    """TestClient usando o banco de teste no lugar do Postgres"""

    def _get_db():
        yield db

    app.dependency_overrides[get_db] = _get_db
    yield TestClient(app)
    app.dependency_overrides.clear()