"""Serve the built frontend from the API's origin (API_SURFACE.md § 0).

Files in the build are served as they are; any other non-API path returns
`index.html`, so the client-side router can take it from there.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse


def mount_frontend(app: FastAPI, dist: Path) -> None:
    """Add a catch-all route for *dist*. Register it after the API routers."""
    root = dist.resolve()
    index = root / "index.html"

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404)
        candidate = (root / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(root):
            return FileResponse(candidate)
        return FileResponse(index)
