from fastapi import APIRouter

from app.routes.v1.worker import router as worker_router

router = APIRouter()
router.include_router(worker_router)
