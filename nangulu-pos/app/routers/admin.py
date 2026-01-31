from fastapi import APIRouter, Depends
from app.dependencies import get_current_admin

router = APIRouter()

@router.get("/dashboard")
async def admin_dashboard(current_user = Depends(get_current_admin)):
    return {"message": f"Welcome Admin {current_user.username}"}