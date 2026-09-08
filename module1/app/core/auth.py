"""Auth-stub layer, reusing Module 2's original RBAC approach exactly
(module2/backend/app/core/auth.py: Role = reviewer | admin) — per the
realignment spec's explicit instruction to extend Module 2's approach here.

Every endpoint requires a recognized actor (`get_current_actor` rejects an
unknown role with 400). Nothing in Module 1 today is sensitive enough to
warrant an admin-only gate the way Module 7's ingestion endpoint is, so
`require_admin` exists for completeness/future use but isn't currently
called anywhere — both reviewer and admin can upload, extract, validate,
save, and browse vendor profiles.

Swapping in real auth means replacing `get_current_actor` only.
"""

from dataclasses import dataclass
from enum import Enum

from fastapi import Header, HTTPException, status


class Role(str, Enum):
    REVIEWER = "reviewer"
    ADMIN = "admin"


@dataclass(frozen=True)
class Actor:
    user_id: str
    role: Role


def get_current_actor(
    x_user_id: str = Header(default="demo-reviewer", alias="X-User-Id"),
    x_user_role: str = Header(default="reviewer", alias="X-User-Role"),
) -> Actor:
    try:
        role = Role(x_user_role.lower())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown role '{x_user_role}'. Expected one of: {[r.value for r in Role]}",
        ) from exc
    return Actor(user_id=x_user_id, role=role)


def require_admin(actor: Actor) -> None:
    if actor.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires the admin role.",
        )
