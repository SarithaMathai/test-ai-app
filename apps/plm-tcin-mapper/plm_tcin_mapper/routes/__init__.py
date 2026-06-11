from fastapi import APIRouter

from plm_tcin_mapper.routes.alias_mining import router as alias_mining_router
from plm_tcin_mapper.routes.eval import router as eval_router
from plm_tcin_mapper.routes.feedback import router as feedback_router
from plm_tcin_mapper.routes.health import router as health_router
from plm_tcin_mapper.routes.ingest import router as ingest_router
from plm_tcin_mapper.routes.mappings import router as mappings_router

router = APIRouter()
router.include_router(health_router)
router.include_router(mappings_router, prefix="/api/v1")
router.include_router(ingest_router, prefix="/api/v1")
router.include_router(eval_router, prefix="/api/v1")
router.include_router(feedback_router, prefix="/api/v1")
router.include_router(alias_mining_router, prefix="/api/v1")
