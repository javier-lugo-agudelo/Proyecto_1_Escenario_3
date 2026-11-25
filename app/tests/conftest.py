import os
import pytest

# Variables de entorno requeridas ANTES de importar la app Flask
os.environ.setdefault("DB_HOST",     "localhost")
os.environ.setdefault("DB_PORT",     "5432")
os.environ.setdefault("DB_NAME",     "test_db")
os.environ.setdefault("DB_USER",     "test_user")
os.environ.setdefault("DB_PASSWORD", "test_pass")
os.environ.setdefault("SECRET_KEY",  "test-secret-key")


@pytest.fixture(scope="session")
def app():
    # init_db() solo se llama bajo __name__ == "__main__", no al importar
    from app import app as flask_app
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()
