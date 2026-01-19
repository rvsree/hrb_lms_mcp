"""SQLAlchemy models matching Java entities."""

from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, ForeignKey, Text, JSON, Boolean, Enum as SQLEnum, CheckConstraint, Computed
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.app.repos.database import Base, engine
import enum


class EmploymentType(enum.Enum):
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    CONTRACTOR = "CONTRACTOR"


class LeaveRequestStatus(enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    PENDING_HITL = "PENDING_HITL"


class HitlRequestStatus(enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Employee(Base):
    """Employee model."""
    __tablename__ = "employees"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    department = Column(String(100))
    manager_id = Column(Integer, ForeignKey("employees.id"))
    hire_date = Column(Date)
    employment_type = Column(SQLEnum(EmploymentType))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    manager = relationship("Employee", remote_side=[id], backref="direct_reports")


class LeaveType(Base):
    """Leave type model."""
    __tablename__ = "leave_types"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    accrual_rate = Column(Numeric(5, 2))
    max_carryover = Column(Integer)
    requires_approval = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class LeaveBalance(Base):
    """Leave balance model."""
    __tablename__ = "leave_balances"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    leave_type_id = Column(Integer, ForeignKey("leave_types.id"), nullable=False)
    accrued = Column(Numeric(5, 2), default=0)
    used = Column(Numeric(5, 2), default=0)
    # Use SQLAlchemy Computed construct for generated column
    available = Column(Numeric(5, 2), Computed("accrued - used", persisted=True))
    year = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    employee = relationship("Employee")
    leave_type = relationship("LeaveType")
    
    # Use the engine dialect to decide sqlite-specific table args. Base.metadata.bind
    # is not set in modern SQLAlchemy, so check engine.dialect.name instead.
    __table_args__ = (
        {"sqlite_autoincrement": True} if getattr(engine, "dialect", None) and engine.dialect.name == "sqlite" else {},
    )


class LeaveRequest(Base):
    """Leave request model."""
    __tablename__ = "leave_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    leave_type_id = Column(Integer, ForeignKey("leave_types.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    days = Column(Numeric(5, 2), nullable=False)
    reason = Column(Text)
    status = Column(SQLEnum(LeaveRequestStatus), default=LeaveRequestStatus.PENDING, nullable=False)
    approver_id = Column(Integer, ForeignKey("employees.id"))
    approved_at = Column(DateTime)
    rejection_reason = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    employee = relationship("Employee", foreign_keys=[employee_id])
    leave_type = relationship("LeaveType")
    approver = relationship("Employee", foreign_keys=[approver_id])
    
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="check_end_after_start"),
    )


class HitlRequest(Base):
    """HITL request model."""
    __tablename__ = "hitl_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    request_type = Column(String(50), nullable=False)
    related_entity_type = Column(String(50))
    related_entity_id = Column(Integer)
    employee_id = Column(Integer, ForeignKey("employees.id"))
    query = Column(Text, nullable=False)
    context = Column(JSON)
    status = Column(SQLEnum(HitlRequestStatus), default=HitlRequestStatus.PENDING, nullable=False)
    assigned_to = Column(String(255))
    response = Column(Text)
    responded_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    employee = relationship("Employee")
