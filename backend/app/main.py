from fastapi import FastAPI

from .config import settings
from .errors import register_error_handlers
from .routers import cases, evidence, health, meta

app = FastAPI(title=f"{settings.product_name} API", version=settings.schema_version)
register_error_handlers(app)
app.include_router(health.router)
app.include_router(meta.router)
app.include_router(cases.router)
app.include_router(evidence.router)