"""
Health Check API Endpoints
Consolidated health check functionality
"""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any
from datetime import datetime
import time

from app.models.requests import ApiResponse


router = APIRouter()


@router.get("/ping", response_model=ApiResponse)
async def ping():
    """Simple ping endpoint"""
    return ApiResponse(
        success=True,
        message="pong",
        data={
            "timestamp": datetime.utcnow().isoformat(),
            "status": "healthy"
        }
    )


@router.get("/health", response_model=ApiResponse)
async def health_check():
    """Comprehensive health check"""
    start_time = time.time()
    
    health_data = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "response_time_ms": 0,
        "services": {
            "api": True,
            "database": False
        }
    }
    
    # Test database connection
    try:
        from app.database.repository_manager import get_user_repo
        user_repo = get_user_repo()
        await user_repo.exists("test-connection")
        health_data["services"]["database"] = True
    except Exception:
        health_data["services"]["database"] = False
    
    health_data["response_time_ms"] = round((time.time() - start_time) * 1000, 2)
    
    return ApiResponse(
        success=True,
        message="Health check completed",
        data=health_data
    )


