import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.bootstrap import create_all_tables, seed_if_empty
from app.config import settings
from app.routers import banking, broker, chat, customers, products

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables + seed baseline data on startup so local dev needs
    # nothing but `pip install` and `uvicorn`. Idempotent on Postgres.
    try:
        await create_all_tables()
        await seed_if_empty()
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Startup bootstrap failed: %s", exc)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="End-to-end mortgage brokerage platform with LLM agent",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(customers.router, prefix="/api/customers", tags=["Customers"])
app.include_router(banking.router, prefix="/api/banking", tags=["Banking"])
app.include_router(products.router, prefix="/api/products", tags=["Products"])
app.include_router(broker.router, prefix="/api/broker", tags=["Broker"])


@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}
