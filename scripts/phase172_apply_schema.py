"""One-off Phase 172 schema apply - same pattern as phase165_apply_schema.py
(no psql client available locally). Idempotent: safe to run more than once.
Run as: python -m scripts.phase172_apply_schema
"""

from sqlalchemy import text

from src.app.repos.database import engine


def main() -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE hrb_emp_lms.specialist_leave_reviews "
                "ADD COLUMN IF NOT EXISTS task_state VARCHAR(20) NOT NULL DEFAULT 'input_required'"
            )
        )
        conn.execute(
            text("ALTER TABLE hrb_emp_lms.specialist_leave_reviews ADD COLUMN IF NOT EXISTS review_brief TEXT")
        )
        conn.execute(
            text("ALTER TABLE hrb_emp_lms.specialist_leave_reviews ADD COLUMN IF NOT EXISTS decision_message JSON")
        )
        conn.execute(
            text("ALTER TABLE hrb_emp_lms.specialist_leave_reviews ADD COLUMN IF NOT EXISTS produced_artifacts JSON")
        )
        print("specialist_leave_reviews.{task_state, review_brief, decision_message, produced_artifacts}: ensured")

    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_schema = 'hrb_emp_lms' AND table_name = 'specialist_leave_reviews' "
                "AND column_name IN ('task_state', 'review_brief', 'decision_message', 'produced_artifacts') "
                "ORDER BY column_name"
            )
        ).fetchall()
        print("\nVerification - new columns present:")
        for row in rows:
            print(f"  {row}")


if __name__ == "__main__":
    main()
