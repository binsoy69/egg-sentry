import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.routers import alerts, auth, dashboard, devices, events, history
from app.seed import seed_defaults
from app.services import evaluate_alerts


settings = get_settings()
logger = logging.getLogger(__name__)


async def alert_evaluator_loop() -> None:
    while True:
        await asyncio.sleep(settings.alert_evaluator_interval_seconds)
        with SessionLocal() as db:
            try:
                evaluate_alerts(db)
                db.commit()
            except Exception:
                db.rollback()
                logger.exception("Alert evaluation loop failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    alert_task = None
    if settings.auto_create_schema:
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            seed_defaults(db)
    if settings.enable_alert_scheduler:
        alert_task = asyncio.create_task(alert_evaluator_loop())
        app.state.alert_evaluator_task = alert_task
    yield
    if alert_task is not None:
        alert_task.cancel()
        with suppress(asyncio.CancelledError):
            await alert_task


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(events.router, prefix=settings.api_prefix)
app.include_router(devices.router, prefix=settings.api_prefix)
app.include_router(dashboard.router, prefix=settings.api_prefix)
app.include_router(history.router, prefix=settings.api_prefix)
app.include_router(alerts.router, prefix=settings.api_prefix)
