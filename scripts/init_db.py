"""Initialise MongoDB collections and indexes for the analysis agent."""

from __future__ import annotations

import asyncio

from app.database import Database
from app.services.run_service import RunService


async def main() -> None:
    service = RunService()
    await service.ensure_indexes()
    await Database.close()


if __name__ == "__main__":
    asyncio.run(main())

