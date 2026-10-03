"""HTTP routers. Each module parses, delegates to a service and maps errors."""

from fastapi import APIRouter

routers: list[APIRouter] = []
