from fastapi import APIRouter

from spark_think_tank_ai.routes import chat, health

router = APIRouter()
router.include_router(health.router)
router.include_router(chat.router)
