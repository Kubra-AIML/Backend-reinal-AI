from fastapi import FastAPI
from .config import settings
from .routers import health

app = FastAPI(title=f"{settings.product_name} API", version=settings.schema_version)
app.include_router(health.router)