"""HTTP routers. Each module parses, delegates to a service and maps errors."""

from fastapi import APIRouter

from app.api import auth

routers: list[APIRouter] = [auth.router]
