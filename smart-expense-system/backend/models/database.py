from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean, DateTime, Text
)
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./expense_data.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True, nullable=False)
    date = Column(String, nullable=True)
    description = Column(Text, nullable=False)
    amount = Column(Float, default=0.0)
    predicted_category = Column(String, nullable=False)
    confidence = Column(Float, default=0.0)
    is_corrected = Column(Boolean, default=False)
    corrected_category = Column(String, nullable=True)
    transaction_type = Column(String, default="debit")   # "debit" | "credit"
    created_at = Column(DateTime, default=datetime.utcnow)

    @property
    def effective_category(self) -> str:
        return self.corrected_category if self.is_corrected else self.predicted_category


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
