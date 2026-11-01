"""API v1 router: all feature routers are registered here."""
from fastapi import APIRouter

from app.api import auth, candidates, dashboard, gdpr, jobs, tasks, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(candidates.router)
api_router.include_router(jobs.router)
api_router.include_router(tasks.router)
api_router.include_router(dashboard.router)
api_router.include_router(gdpr.router)
