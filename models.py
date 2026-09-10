from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base

class Cat(Base):
    __tablename__ = "cats"

    cat_id = Column(String, primary_key=True, index=True)
    name = Column(String)
    token = Column(String)
    is_active = Column(Boolean, default=True)

    scan_logs = relationship("ScanLog", back_populates="cat")

class ScanLog(Base):
    __tablename__ = "scan_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    employee_id = Column(String, index=True)
    name = Column(String)
    department = Column(String)
    cat_id = Column(String, ForeignKey("cats.cat_id"))
    status = Column(String) # 'FOUND' or 'DUPLICATE'

    cat = relationship("Cat", back_populates="scan_logs")

class Participant(Base):
    __tablename__ = "participants"

    employee_id = Column(String, primary_key=True, index=True)
    name = Column(String)
    department = Column(String)
    first_scan_at = Column(DateTime(timezone=True), nullable=True)
    last_scan_at = Column(DateTime(timezone=True), nullable=True)
    total_found = Column(Integer, default=0)
    is_completed = Column(Boolean, default=False)
