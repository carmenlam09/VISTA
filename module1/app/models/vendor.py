"""SQLAlchemy ORM tables — table and column names are frozen to match
module1/database/schema.sql exactly (the schema Modules 2-7 already read),
with one additive change: `id_number` on directors/shareholders/ubos (see
app/schemas/vendor.py for why). `app/db/session.py::init_db()` ALTERs
existing databases to add these columns in place, so the real, already
populated vista.db upgrades without any data loss.
"""

from sqlalchemy import ForeignKey, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Vendor(Base):
    __tablename__ = "vendors"

    vendor_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vendor_name: Mapped[str] = mapped_column(String, nullable=False)
    registration_number: Mapped[str | None] = mapped_column(String, nullable=True)
    country: Mapped[str | None] = mapped_column(String, nullable=True)
    address: Mapped[str | None] = mapped_column(String, nullable=True)
    created_date: Mapped[str] = mapped_column(String, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    directors: Mapped[list["Director"]] = relationship(back_populates="vendor", cascade="all, delete-orphan")
    shareholders: Mapped[list["Shareholder"]] = relationship(back_populates="vendor", cascade="all, delete-orphan")
    ubos: Mapped[list["Ubo"]] = relationship(back_populates="vendor", cascade="all, delete-orphan")
    related_parties: Mapped[list["RelatedParty"]] = relationship(back_populates="vendor", cascade="all, delete-orphan")


class Director(Base):
    __tablename__ = "directors"

    director_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.vendor_id", ondelete="CASCADE"), nullable=False)
    director_name: Mapped[str] = mapped_column(String, nullable=False)
    nationality: Mapped[str | None] = mapped_column(String, nullable=True)
    id_number: Mapped[str | None] = mapped_column(String, nullable=True)

    vendor: Mapped["Vendor"] = relationship(back_populates="directors")


class Shareholder(Base):
    __tablename__ = "shareholders"

    shareholder_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.vendor_id", ondelete="CASCADE"), nullable=False)
    shareholder_name: Mapped[str] = mapped_column(String, nullable=False)
    ownership_percentage: Mapped[float | None] = mapped_column(nullable=True)
    id_number: Mapped[str | None] = mapped_column(String, nullable=True)

    vendor: Mapped["Vendor"] = relationship(back_populates="shareholders")


class Ubo(Base):
    __tablename__ = "ubos"

    ubo_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.vendor_id", ondelete="CASCADE"), nullable=False)
    ubo_name: Mapped[str] = mapped_column(String, nullable=False)
    ownership_percentage: Mapped[float | None] = mapped_column(nullable=True)
    id_number: Mapped[str | None] = mapped_column(String, nullable=True)

    vendor: Mapped["Vendor"] = relationship(back_populates="ubos")


class RelatedParty(Base):
    __tablename__ = "related_parties"

    related_party_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.vendor_id", ondelete="CASCADE"), nullable=False)
    related_party_name: Mapped[str] = mapped_column(String, nullable=False)
    relationship_type: Mapped[str | None] = mapped_column(String, nullable=True)

    vendor: Mapped["Vendor"] = relationship(back_populates="related_parties")
