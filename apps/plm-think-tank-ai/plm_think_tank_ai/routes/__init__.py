from fastapi import APIRouter

from plm_think_tank_ai.routes import health, prompts

router = APIRouter()
router.include_router(health.router)
router.include_router(prompts.router)
