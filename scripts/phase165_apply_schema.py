"""One-off Phase 165 schema apply - no psql client available locally, same
reasoning as every other ad-hoc DB script in this project. Idempotent:
safe to run more than once. Run as: python -m scripts.phase165_apply_schema
"""

from sqlalchemy import text

from src.app.repos.database import Base, engine
from src.app.models.models import SpecialistLeaveReview, UnpaidLeaveDocument  # noqa: F401 - registers tables on Base.metadata


def main() -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE hrb_emp_lms.leave_types "
                "ADD COLUMN IF NOT EXISTS requires_specialist_review BOOLEAN NOT NULL DEFAULT false"
            )
        )
        print("leave_types.requires_specialist_review: ensured")

    Base.metadata.create_all(bind=engine, tables=[UnpaidLeaveDocument.__table__, SpecialistLeaveReview.__table__])
    print("unpaid_leave_documents, specialist_leave_reviews: ensured")

    with engine.begin() as conn:
        conn.execute(text("UPDATE hrb_emp_lms.leave_types SET requires_specialist_review = true WHERE code = 'UNPAID'"))

        for code, name in [
            ("CRITICAL_CAREGIVER", "Critical CareGiver Leave"),
            ("STD", "Short-Term Disability"),
            ("LTD", "Long-Term Disability"),
        ]:
            conn.execute(
                text(
                    "INSERT INTO hrb_emp_lms.leave_types (code, name, requires_approval, requires_specialist_review) "
                    "VALUES (:code, :name, true, true) ON CONFLICT (code) DO NOTHING"
                ),
                {"code": code, "name": name},
            )
        print("leave_types seed rows (CRITICAL_CAREGIVER/STD/LTD): ensured")

    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT code, name, requires_approval, requires_specialist_review FROM hrb_emp_lms.leave_types "
                "WHERE code IN ('UNPAID', 'CRITICAL_CAREGIVER', 'STD', 'LTD') ORDER BY code"
            )
        ).fetchall()
        print("\nVerification - leave_types rows:")
        for row in rows:
            print(f"  {row}")

        table_rows = conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'hrb_emp_lms' AND table_name IN ('unpaid_leave_documents', 'specialist_leave_reviews')"
            )
        ).fetchall()
        print("\nVerification - new tables present:")
        for row in table_rows:
            print(f"  {row}")


if __name__ == "__main__":
    main()
