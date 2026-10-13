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
    # Schema-qualified directly rather than relying on the session-level
    # `SET search_path` in database.py's connect event listener - Neon's
    # pooled endpoint (the "-pooler" host) is PgBouncer in transaction
    # pooling mode, which can silently remap a logical connection to a
    # different backend server process between transactions. Session state
    # like search_path set on one backend doesn't carry over to another,
    # so an unqualified "FROM employees" intermittently fails with
    # "relation employees does not exist" depending on which backend
    # PgBouncer happens to route a given transaction to. Qualifying the
    # schema here makes every generated query self-contained, independent
    # of any server-side session state.
    __table_args__ = {"schema": "hrb_emp_lms"}

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    department = Column(String(100))
    manager_id = Column(Integer, ForeignKey("hrb_emp_lms.employees.id"))
    hire_date = Column(Date)
    employment_type = Column(SQLEnum(EmploymentType))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    manager = relationship("Employee", remote_side=[id], backref="direct_reports")


class LeaveType(Base):
    """Leave type model."""
    __tablename__ = "leave_types"
    __table_args__ = {"schema": "hrb_emp_lms"}

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    accrual_rate = Column(Numeric(5, 2))
    max_carryover = Column(Integer)
    requires_approval = Column(Boolean, default=True, nullable=False)
    # Phase 165 - separate from requires_approval, which means "needs a
    # manager". UNPAID/CRITICAL_CAREGIVER/STD/LTD all set this true - a
    # human HR specialist reviews these via the HITL flow, never a manager.
    requires_specialist_review = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class LeaveBalance(Base):
    """Leave balance model."""
    __tablename__ = "leave_balances"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("hrb_emp_lms.employees.id"), nullable=False)
    leave_type_id = Column(Integer, ForeignKey("hrb_emp_lms.leave_types.id"), nullable=False)
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
    # "schema" merged into the same dict - SQLAlchemy requires the dict of
    # table-level kwargs to be the single/last element of __table_args__.
    # Sqlite doesn't support cross-schema the same way Postgres does, so
    # schema is only added for the real (Postgres) dialect - not currently
    # exercised anywhere in this codebase, but kept consistent with the
    # existing sqlite_autoincrement guard rather than assuming it never will be.
    _is_sqlite = bool(getattr(engine, "dialect", None) and engine.dialect.name == "sqlite")
    __table_args__ = (
        {
            **({"sqlite_autoincrement": True} if _is_sqlite else {"schema": "hrb_emp_lms"}),
        },
    )


class LeaveRequest(Base):
    """Leave request model."""
    __tablename__ = "leave_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("hrb_emp_lms.employees.id"), nullable=False)
    leave_type_id = Column(Integer, ForeignKey("hrb_emp_lms.leave_types.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    days = Column(Numeric(5, 2), nullable=False)
    reason = Column(Text)
    status = Column(SQLEnum(LeaveRequestStatus), default=LeaveRequestStatus.PENDING, nullable=False)
    approver_id = Column(Integer, ForeignKey("hrb_emp_lms.employees.id"))
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
        {"schema": "hrb_emp_lms"},
    )


class HitlRequest(Base):
    """HITL request model."""
    __tablename__ = "hitl_requests"
    __table_args__ = {"schema": "hrb_emp_lms"}

    id = Column(Integer, primary_key=True, index=True)
    request_type = Column(String(50), nullable=False)
    related_entity_type = Column(String(50))
    related_entity_id = Column(Integer)
    employee_id = Column(Integer, ForeignKey("hrb_emp_lms.employees.id"))
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


class LeaveReviewDecision(enum.Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class UnpaidLeaveDocument(Base):
    """Phase 165 - the manifest for a leave request's supporting document(s).
    leave_request_id is nullable on purpose: the employee-facing upload flow
    uploads to S3 before the leave request exists (confirmed by reading
    hrb_chatbot_ui's UnpaidLeaveModal.tsx directly), so this row is created
    at upload time (leave_request_id still null) and linked once submit
    actually creates the leave request - otherwise a failed submit after a
    successful upload leaves a real S3 object with nothing in any database
    pointing at it, a real silent-orphan bug, not a hypothetical one."""
    __tablename__ = "unpaid_leave_documents"
    __table_args__ = {"schema": "hrb_emp_lms"}

    id = Column(Integer, primary_key=True, index=True)
    s3_key = Column(String(512), unique=True, nullable=False, index=True)
    leave_request_id = Column(Integer, ForeignKey("hrb_emp_lms.leave_requests.id"), nullable=True, index=True)
    original_filename = Column(String(255), nullable=False)
    content_type = Column(String(100))
    uploaded_at = Column(DateTime, server_default=func.now())

    leave_request = relationship("LeaveRequest")


class SpecialistLeaveReview(Base):
    """Phase 165 - the full HITL review lifecycle for a leave request that
    needs specialist review (requires_specialist_review=True leave types),
    with real typed columns instead of overloading hitl_requests.assigned_to
    with a name string the way the pre-Phase-165 flow did. Covers all such
    leave types, not just unpaid - deliberately not named "unpaid_leave_*".
    "Elapsed time" is deliberately not a column here - it's
    responded_at - created_at (or now() - created_at while still pending),
    computed by the caller at read time, so it can never go stale."""
    __tablename__ = "specialist_leave_reviews"
    __table_args__ = {"schema": "hrb_emp_lms"}

    id = Column(Integer, primary_key=True, index=True)
    hitl_request_id = Column(Integer, ForeignKey("hrb_emp_lms.hitl_requests.id"), nullable=False, index=True)
    leave_request_id = Column(Integer, ForeignKey("hrb_emp_lms.leave_requests.id"), nullable=False, index=True)
    leave_type_code = Column(String(50), nullable=False)
    status = Column(SQLEnum(HitlRequestStatus), default=HitlRequestStatus.PENDING, nullable=False)
    decision = Column(SQLEnum(LeaveReviewDecision), nullable=True)
    hr_specialist_employee_id = Column(Integer, ForeignKey("hrb_emp_lms.employees.id"), nullable=True)
    hr_comments = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    responded_at = Column(DateTime, nullable=True)
    # Phase 172 - A2A-shaped vocabulary, additive alongside `status` above
    # (left unchanged, still PENDING/COMPLETED - every existing caller of
    # it keeps working). task_state is the real Task lifecycle value
    # (submitted/working/input_required/completed/rejected) this project's
    # own agent graph tracks - "submitted"/"working" only ever hold true
    # transiently inside one synchronous request before this row is first
    # written, so only input_required/completed/rejected are ever actually
    # persisted here. review_brief is the specialist-facing LLM-generated
    # summary (the "Review-support agent" the original design called for).
    # decision_message/produced_artifacts are plain JSON, not a real A2A
    # wire payload - Message/Parts and Artifact *shaped*, for this
    # project's own internal use, not interop with another A2A server.
    task_state = Column(String(20), nullable=False, default="input_required")
    review_brief = Column(Text, nullable=True)
    decision_message = Column(JSON, nullable=True)
    produced_artifacts = Column(JSON, nullable=True)

    hitl_request = relationship("HitlRequest")
    leave_request = relationship("LeaveRequest")
    hr_specialist = relationship("Employee")
