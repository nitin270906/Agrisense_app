"""FastAPI application factory.

The built frontend is mounted from this same app when `frontend/dist` exists.
That single-origin arrangement removes an entire class of demo failure: no CORS
preflight, no second process, no separate URL to remember on stage. Running the
Vite dev server separately still works — CORS is configured for it.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request

from app.config import FRONTEND_DIST, settings
from app.database import init_db
from app.ml.predictor import predictor
from app.routers import dashboard, farms, insights, meta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if predictor.load():
        logger.info("Models ready (v%s)", predictor.model_version)
    else:
        # Not fatal: prediction falls back to the physics simulator, so the API
        # is fully usable before `python -m app.ml.train` has ever been run.
        logger.warning(
            "Model artifacts not found — using physics fallback. "
            "Run `python -m app.ml.train` to enable ML predictions."
        )
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description=(
            "Forecasts soil salinity, crop water stress, irrigation need and crop "
            "health from sensor and weather data.\n\n"
            "**Data note:** models are trained on physics-simulated data derived "
            "from FAO-56 and Maas-Hoffman relationships, not field measurements. "
            "See `/api/model/info` for full provenance."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for router in (meta.router, farms.router, insights.router, dashboard.router):
        app.include_router(router, prefix=settings.api_prefix)

    @app.exception_handler(Exception)
    async def unhandled_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "path": request.url.path},
        )

    _mount_frontend(app)
    return app


def _mount_frontend(app: FastAPI) -> None:
    """Serve the built SPA, if present, with history-mode fallback."""
    if not FRONTEND_DIST.exists():
        @app.get("/", include_in_schema=False)
        def dev_root() -> dict:
            return {
                "app": settings.app_name,
                "docs": "/docs",
                "note": "Frontend not built. Run `npm run dev` in ./frontend.",
            }
        return

    assets = FRONTEND_DIST / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    index = FRONTEND_DIST / "index.html"

    @app.get("/", include_in_schema=False)
    def spa_root() -> FileResponse:
        return FileResponse(index)

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str) -> FileResponse:
        """Return index.html for client-side routes.

        Registered last so it never shadows /api or /docs; a direct hit on a
        static file is served from disk when it exists.
        """
        candidate = FRONTEND_DIST / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index)


app = create_app()
