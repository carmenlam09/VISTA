"""Auth-stub layer, extending Module 2's original RBAC approach
(module2/backend/app/core/auth.py: Role = reviewer | admin) rather than
Module 5/6's later 3-role Maker-Checker extension — this module has no
approve/reject workflow, so `approver` doesn't apply here.

Historical records span every vendor the bank has ever reviewed — one of
the most sensitive stores in the platform. Retrieval is restricted to
reviewer/admin. Ingestion is admin-only: it's a system/service-level write
(meant to be called by other modules' backends, not a human reviewer's
day-to-day action), so it's gated more tightly than read access.

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


def require_authorized(actor: Actor) -> None:
    """Both roles are 'authorized' by definition today — this exists so a
    future, narrower role added to this enum doesn't silently gain read
    access to the historical record store."""
    if actor.role not in (Role.REVIEWER, Role.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to the knowledge repository requires an authorized reviewer/admin role.",
        )


def require_admin(actor: Actor) -> None:
    if actor.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ingesting knowledge records requires the admin role.",
        )
