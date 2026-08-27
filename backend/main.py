from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from dotenv import load_dotenv

from app.core.config import settings
from app.core.database import init_db
from app.api import cloud_config
from app.api.topology import router as topology_router

load_dotenv()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database...")
    await init_db()
    yield

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=86400,
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception at {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "An internal server error occurred."}
    )

# Register routes
app.include_router(cloud_config.router, prefix=settings.API_V1_STR)
app.include_router(topology_router, prefix=settings.API_V1_STR + "/topology", tags=["Topology"])

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "service": settings.APP_NAME}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
