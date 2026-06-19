from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    analytics,
    auth,
    compliance,
    device_tokens,
    dlq,
    events,
    notifications,
    preferences,
    templates,
    users,
    webhooks,
)

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(events.router)
api_router.include_router(users.router)
api_router.include_router(notifications.router)
api_router.include_router(preferences.router)
api_router.include_router(templates.router)
api_router.include_router(analytics.router)
api_router.include_router(device_tokens.router)
api_router.include_router(admin.router)
api_router.include_router(webhooks.router)
api_router.include_router(dlq.router)
api_router.include_router(compliance.router)
