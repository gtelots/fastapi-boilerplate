"""Item database model."""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.kit.db.models import RecordModel


class Item(RecordModel):
    """Item model for storing item data."""

    __tablename__ = "items"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[int] = mapped_column(nullable=False)  # Price in cents
    quantity: Mapped[int] = mapped_column(nullable=False, default=0)
    sku: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True, index=True)

    def __repr__(self) -> str:
        return f"Item(id={self.id!r}, name={self.name!r}, price={self.price})"

