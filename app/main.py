"""FastAPI application entry point for the test run analysis agent."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .api import dashboard as dashboard_routes
from .api import runs as runs_routes
from .database import Database
from .services.run_service import RunService


app = FastAPI(title="Test Run Analysis Agent", version="0.1.0")

templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(runs_routes.router)
app.include_router(dashboard_routes.router)


@app.on_event("startup")
async def startup_event() -> None:
    service = RunService()
    await service.ensure_indexes()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await Database.close()


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("dashboard.html", {"request": request})

