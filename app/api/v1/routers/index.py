"""
Router utama API v1
"""
from fastapi import APIRouter
from .chatbot import router as chatbot_router


router = APIRouter()

# Include chatbot router
router.include_router(chatbot_router)

@router.get("/")
def read_root():
    return {"message": "OriensSpace AI API v1"}