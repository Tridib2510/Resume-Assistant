from fastapi import APIRouter

from api.v1.endpoints.graph import router as graph_router

router = APIRouter()
router.include_router(graph_router, prefix="/graph")