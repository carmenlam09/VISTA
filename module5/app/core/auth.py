"""Auth-stub layer, extending Module 2's RBAC approach
(module2/backend/app/core/auth.py) rather than inventing a new one, per the
spec's explicit instruction.

Module 2's Role was `reviewer | admin`. Module 5 adds `approver`: risk
assessment drafts are Maker-Checker — a reviewer can view and edit a draft,
but approving it (the "Checker" step) requires the approver (or admin)
role, so a reviewer can't self-approve their own draft. This is a
role-based gate only, not a full separation-of-duties check (it doesn't
verify the approver is a *different person* from whoever last edited the
draft) — see module5/README.md Assumptions.

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
    """Risk assessment drafts are sensitive (marked 'Confidential' in the
    source policy doc) — restricted to reviewer/approver/admin, i.e. any
    role recognized by this stub. In practice every role currently defined
    passes this gate; it exists so a future, narrower role added to this
    enum doesn't silently gain access to draft assessments."""
    if actor.role not in AUTHORIZED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to risk assessment drafts requires an authorized reviewer/approver role.",
        )


def require_approval_role(actor: Actor) -> None:
    if actor.role not in APPROVAL_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Approving a risk assessment draft requires the approver or admin role.",
        )
