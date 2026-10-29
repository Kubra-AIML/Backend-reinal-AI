import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import settings
from .db import SessionLocal
from .errors import register_error_handlers
from .routers import cases, evidence, health, meta, models, queue, reports
from .services.engine_audit import record_engine_mode_if_changed

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        with SessionLocal() as db:
            record_engine_mode_if_changed(db, settings.engine_mode)
    except Exception:  # e.g. database not migrated yet; /api/health reports that state
        log.warning("Could not record the engine mode (is the database migrated?)")
    yield


app = FastAPI(title=f"{settings.product_name} API", version=settings.schema_version, lifespan=lifespan)
register_error_handlers(app)
app.include_router(health.router)
app.include_router(meta.router)
app.include_router(cases.router)
app.include_router(queue.router)
app.include_router(reports.router)
app.include_router(models.router)
app.include_router(evidence.router)