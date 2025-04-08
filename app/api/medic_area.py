from fastapi import APIRouter, Request
from fastapi.responses import ORJSONResponse

router = APIRouter(
    prefix="/medic/",
    tags=["medic"]
)