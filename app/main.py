from fastapi import FastAPI
import os

app = FastAPI(
    title="Nangulu Chicken Feed POS",
    description="Production POS System - KGs as source of truth",
    version="1.0.0"
)

@app.get("/")
async def root():
    return {"message": "Nangulu Chicken Feed POS", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "nangulu-pos"}
