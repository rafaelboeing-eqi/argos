from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base for Argos-owned tables only (argos_*). Legacy tables are never modeled here."""
