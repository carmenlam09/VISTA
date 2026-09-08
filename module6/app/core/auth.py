"""Auth-stub layer, extending Module 5's RBAC approach
(module5/app/core/auth.py) rather than inventing a new one.

Generated reports carry the same sensitivity as the Module 5 risk
assessments they're built from — restricted to reviewer/approver/admin.
Moving a report to `approved` (the Checker step, mirroring Module 5's draft
approval) requires approver/admin, so a reviewer can't self-approve their
own report.

Swapping in real auth means replacing `get_current_actor` only.
"""

from dataclasses import dataclass
from enum import Enum

from fastapi import Header, HTTPException, status


class Role(str, Enum):
    REVIEWER = "reviewer"
    APPROVER = "approver"
    ADMIN = "admin"


AUTHORIZED_ROLES = {Role.REVIEWER, Role.APPROVER, Role.ADMIN}
APPROVAL_ROLES = {Role.APPROVER, Role.ADMIN}


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
    if actor.role not in AUTHORIZED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to draft KYV reports requires an authorized reviewer/approver role.",
        )


def require_approval_role(actor: Actor) -> None:
    if actor.role not in APPROVAL_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Approving a KYV report requires the approver or admin role.",
        )
