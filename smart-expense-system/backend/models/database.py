from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, text
)
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os

_raw_url = os.getenv("DATABASE_URL", "sqlite:///./expense_data.db")
# Render provides postgres:// but SQLAlchemy 2.x requires postgresql://
DATABASE_URL = _raw_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False, default="")
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
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


class UploadSession(Base):
    __tablename__ = "upload_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    session_id = Column(String, unique=True, index=True, nullable=False)
    filename = Column(String, nullable=True)
    upload_date = Column(DateTime, default=datetime.utcnow)
    total_transactions = Column(Integer, default=0)
    total_spend = Column(Float, default=0.0)
    total_income = Column(Float, default=0.0)
    date_range_start = Column(String, nullable=True)
    date_range_end = Column(String, nullable=True)
    top_category = Column(String, nullable=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    # Add user_id columns to existing tables if missing (safe migration for SQLite)
    with engine.connect() as conn:
        for stmt in [
            "ALTER TABLE transactions ADD COLUMN user_id INTEGER REFERENCES users(id)",
            "ALTER TABLE upload_sessions ADD COLUMN user_id INTEGER REFERENCES users(id)",
        ]:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception:
                pass  # Column already exists
