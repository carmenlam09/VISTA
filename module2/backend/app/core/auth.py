"""Auth-stub layer.

Mirrors the boundary a real deployment would have: an upstream identity
provider (SSO/JWT) injects an authenticated actor with a role, and every
downstream service call trusts that actor. Here the actor is read from plain
request headers so the rest of the app (RBAC checks, audit logging) can be
built and tested against a stable contract. Swapping in real auth means
replacing only `get_current_actor` below — no other file needs to change.
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
