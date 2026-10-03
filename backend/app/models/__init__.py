"""SQLAlchemy model package.

Importing this module registers every table on the shared metadata, which is
what `flask db migrate` and `db.create_all()` rely on.
"""

from app.models.budget import Budget
from app.models.concept import Concept
from app.models.setting import Setting
from app.models.transaction import Transaction
from app.models.user import User

__all__ = ["Budget", "Concept", "Setting", "Transaction", "User"]
