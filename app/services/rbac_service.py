"""RBAC service — seed, checks, role CRUD helpers."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.enums import UserRole
from app.models.rbac import Permission, Role, RolePermission
from app.models.user import User
from app.rbac_catalog import PERMISSION_CATALOG, ROLE_DEFAULTS


def ensure_rbac_seed(session: Session) -> None:
    """Idempotent seed of permissions + system roles."""
    existing = {p.code: p for p in session.scalars(select(Permission)).all()}
    for code, name, desc, group in PERMISSION_CATALOG:
        if code in existing:
            perm = existing[code]
            perm.name = name
            perm.description = desc
            perm.group_name = group
        else:
            perm = Permission(code=code, name=name, description=desc, group_name=group)
            session.add(perm)
            existing[code] = perm
    session.flush()

    all_codes = list(existing.keys())
    for slug, meta in ROLE_DEFAULTS.items():
        role = session.scalar(select(Role).where(Role.slug == slug))
        if not role:
            role = Role(
                slug=slug,
                name=meta["name"],
                description=meta["description"],
                is_system=meta["is_system"],
            )
            session.add(role)
            session.flush()
        else:
            role.name = meta["name"]
            role.description = meta["description"]
            role.is_system = meta["is_system"]

        wanted = set(all_codes if "*" in meta["permissions"] else meta["permissions"])
        rps = list(
            session.scalars(
                select(RolePermission)
                .where(RolePermission.role_id == role.id)
                .options(selectinload(RolePermission.permission))
            ).all()
        )
        current = {rp.permission.code for rp in rps if rp.permission}
        for code in wanted - current:
            perm = existing.get(code)
            if perm:
                session.add(RolePermission(role_id=role.id, permission_id=perm.id))
        for rp in rps:
            if rp.permission and rp.permission.code not in wanted:
                session.delete(rp)

    session.flush()

    # Link users without role_id to matching system role by enum
    roles_by_slug = {
        r.slug: r for r in session.scalars(select(Role)).all()
    }
    for user in session.scalars(select(User).where(User.role_id.is_(None))).all():
        slug = user.role.value if hasattr(user.role, "value") else str(user.role)
        if slug in roles_by_slug:
            user.role_id = roles_by_slug[slug].id


def get_user_permission_codes(session: Session, user: User) -> set[str]:
    role = None
    if user.role_id:
        role = session.scalar(
            select(Role)
            .where(Role.id == user.role_id)
            .options(selectinload(Role.permissions).selectinload(RolePermission.permission))
        )
    if not role:
        slug = user.role.value if hasattr(user.role, "value") else str(user.role)
        role = session.scalar(
            select(Role)
            .where(Role.slug == slug)
            .options(selectinload(Role.permissions).selectinload(RolePermission.permission))
        )
    if not role:
        return set()
    return {rp.permission.code for rp in role.permissions if rp.permission}


def user_has_permission(session: Session, user: User, code: str) -> bool:
    # Legacy admin enum always allowed
    role_val = user.role.value if hasattr(user.role, "value") else str(user.role)
    if role_val == UserRole.admin.value:
        return True
    return code in get_user_permission_codes(session, user)


def sync_user_enum_from_role(session: Session, user: User) -> None:
    """Keep legacy users.role enum aligned with perfil slug when possible."""
    if not user.role_id:
        return
    role = session.get(Role, user.role_id)
    if not role:
        return
    try:
        user.role = UserRole(role.slug)
    except ValueError:
        # custom profile — keep previous enum, prefer member for access gates
        if user.role == UserRole.admin:
            user.role = UserRole.member
