"""One-off live verification for admin_delete_hitl_request - this project
has no test suite, same direct-verification pattern every prior phase used.
Run as: python -m scripts.phase168_live_verify
"""

from datetime import date, timedelta

from sqlalchemy import text

from src.app.repos.database import SessionLocal
from src.app.services.leave_request_service import LeaveRequestService
from src.app.services.hitl_service import HitlService


def main() -> None:
    db = SessionLocal()
    try:
        leave_service = LeaveRequestService(db)
        hitl_service = HitlService(db)

        doc = leave_service.register_leave_document(
            "EMP052", f"phase168-verify-{date.today().isoformat()}.pdf", "to-be-deleted.pdf", "application/pdf"
        )
        print("1. registered document:", doc)

        start = date.today() + timedelta(days=40)
        end = start + timedelta(days=2)
        submit_result = leave_service.submit_unpaid_leave_request(
            employee_id="EMP052",
            start_date=start,
            end_date=end,
            purpose="Phase 168 admin-delete verification",
            is_repeat_within_12_months=False,
            leave_type_code="LTD",
            document_reference=doc["s3Key"],
        )
        print("2. submitted:", submit_result)
        hitl_request_id = submit_result["hitlRequestId"]
        leave_request_id = submit_result["requestId"]

        delete_result = hitl_service.admin_delete_hitl_request(hitl_request_id)
        print("3. deleted:", delete_result)
        assert delete_result["deletedLeaveRequest"] is True
        assert delete_result["deletedSpecialistLeaveReviews"] == 1
        assert delete_result["deletedDocumentS3Keys"] == [doc["s3Key"]]

        # Confirm everything is actually gone, not just that delete returned ok.
        hitl_gone = db.execute(text("SELECT 1 FROM hrb_emp_lms.hitl_requests WHERE id = :id"), {"id": hitl_request_id}).fetchone()
        leave_gone = db.execute(text("SELECT 1 FROM hrb_emp_lms.leave_requests WHERE id = :id"), {"id": leave_request_id}).fetchone()
        review_gone = db.execute(
            text("SELECT 1 FROM hrb_emp_lms.specialist_leave_reviews WHERE hitl_request_id = :id"), {"id": hitl_request_id}
        ).fetchone()
        doc_gone = db.execute(
            text("SELECT 1 FROM hrb_emp_lms.unpaid_leave_documents WHERE s3_key = :k"), {"k": doc["s3Key"]}
        ).fetchone()
        print("4. verification - all should be None:", hitl_gone, leave_gone, review_gone, doc_gone)
        assert hitl_gone is None and leave_gone is None and review_gone is None and doc_gone is None

        print("\nALL PHASE 168 LIVE CHECKS PASSED")
    finally:
        db.close()


if __name__ == "__main__":
    main()
