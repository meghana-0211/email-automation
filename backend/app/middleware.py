from fastapi import Request, HTTPException
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import time
from typing import Callable
import jwt
import uuid
from pydantic import BaseSettings

class Settings(BaseSettings):
    API_KEY: str

    class Config:
        env_file = ".env"  # Path to environment variables file

settings = Settings()


api_key_header = APIKeyHeader(name="X-API-Key")

class AuthenticationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        if request.url.path.startswith("/api"):
            api_key = request.headers.get("X-API-Key")
            if not api_key or api_key != settings.API_KEY.get_secret_value():
                raise HTTPException(status_code=403, detail="Invalid API key")
        return await call_next(request)

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        start_time = time.time()
        
        # Setup request logging
        request_id = str(uuid.uuid4())
        logging.info(f"Request {request_id} started: {request.method} {request.url}")
        
        try:
            response = await call_next(request)
            process_time = (time.time() - start_time) * 1000
            response.headers["X-Process-Time"] = str(process_time)
            logging.info(f"Request {request_id} completed: {response.status_code} ({process_time:.2f}ms)")
            return response
        except Exception as e:
            logging.error(f"Request {request_id} failed: {str(e)}")
            raise

class RequestValidationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        # Validate request size
        if request.headers.get("content-length"):
            if int(request.headers["content-length"]) > 10 * 1024 * 1024:  # 10MB limit
                raise HTTPException(status_code=413, detail="Request too large")
        
        return await call_next(request)