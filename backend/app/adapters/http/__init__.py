"""HTTP adapter: FastAPI routers that parse, call a use case and shape the result."""

from fastapi import APIRouter

from app.adapters.http import (
    auth,
    budgets,
    history,
    household,
    me,
    members,
    overview,
    transactions,
)

routers: list[APIRouter] = [
    auth.router,
    me.router,
    household.router,
    members.router,
    budgets.router,
    transactions.router,
    overview.router,
    history.router,
]
