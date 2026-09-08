"""Auth-stub layer, matching Module 2's pattern (module2/backend/app/core/
auth.py). Module 4 has no RBAC gate to enforce, but the override endpoint
needs to know *who* is overriding a recommendation for the audit trail —
this is that boundary. Swapping in real auth means replacing
`get_current_actor` only."""

from dataclasses import dataclass

from fastapi import Header


@dataclass(frozen=True)
class Actor:
    user_id: str
    role: str


def get_current_actor(
    x_user_id: str = Header(default="demo-reviewer", alias="X-User-Id"),
    x_user_role: str = Header(default="reviewer", alias="X-User-Role"),
) -> Actor:
    return Actor(user_id=x_user_id, role=x_user_role)
