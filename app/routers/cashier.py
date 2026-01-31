from fastapi import APIRouter, Depends
from app.dependencies import get_current_cashier

router = APIRouter()

@router.get("/dashboard")
async def cashier_dashboard(current_user = Depends(get_current_cashier)):
    return {"message": f"Welcome Cashier {current_user.username}"}
