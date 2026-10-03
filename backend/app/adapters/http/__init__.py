"""HTTP adapter: FastAPI routers that parse, call a use case and shape the result."""

from fastapi import APIRouter

from app.adapters.http import auth, household, me, members

routers: list[APIRouter] = [auth.router, me.router, household.router, members.router]
