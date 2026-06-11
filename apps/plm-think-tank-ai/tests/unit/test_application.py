import pytest
from fastapi import FastAPI
from plm_think_tank_ai.main import create_app


@pytest.mark.unit
def test_create_app_returns_fastapi_instance():
    app = create_app()
    assert isinstance(app, FastAPI)
    assert app.title == "PLM Think Tank AI"
