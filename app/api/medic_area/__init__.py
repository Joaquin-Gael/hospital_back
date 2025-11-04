"""Modular routers for the medical area."""
from fastapi import APIRouter
from fastapi.responses import ORJSONResponse

from . import (
    appointments,
    chat,
    departments,
    doctors,
    health_insurance,
    locations,
    schedules,
    services,
    specialties,
    turns,
)

router = APIRouter(prefix="/medic", default_response_class=ORJSONResponse)

router.include_router(schedules.router)
router.include_router(doctors.router)
router.include_router(locations.router)
router.include_router(services.router)
router.include_router(specialties.router)
router.include_router(chat.router)
router.include_router(departments.router)
router.include_router(turns.router)
router.include_router(appointments.router)
router.include_router(health_insurance.router)

__all__ = ["router"]
