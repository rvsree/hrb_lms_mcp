"""One-off live verification for Phase 165's new service methods against
the real local Postgres database - this project has no test suite of its
own, same direct-verification pattern Phase 162 already used.
Run as: python -m scripts.phase165_live_verify
"""

from datetime import date, timedelta

from src.app.repos.database import SessionLocal
from src.app.services.leave_request_service import LeaveRequestService
from src.app.services.hitl_service import HitlService


def main() -> None:
    db = SessionLocal()
    try:
        leave_service = LeaveRequestService(db)
        hitl_service = HitlService(db)

        # 1. Register a document manifest row BEFORE any leave request exists.
        doc = leave_service.register_leave_document(
            employee_id="EMP052",
            s3_key=f"std/EMP052/phase165-verify-{date.today().isoformat()}.pdf",
            original_filename="doctor-note.pdf",
            content_type="application/pdf",
        )
        print("1. register_leave_document:", doc)
        assert doc["s3Key"]

        # 2. Submit an STD leave request, linking that same document.
        start = date.today() + timedelta(days=5)
        end = start + timedelta(days=3)
        submit_result = leave_service.submit_unpaid_leave_request(
            employee_id="EMP052",
            start_date=start,
            end_date=end,
            purpose="Phase 165 live verification - STD request",
            is_repeat_within_12_months=False,
            leave_type_code="STD",
            document_reference=doc["s3Key"],
        )
        print("2. submit_unpaid_leave_request:", submit_result)
        assert submit_result["leaveType"] == "STD"
        request_id = submit_result["requestId"]
        hitl_request_id = submit_result["hitlRequestId"]

        # 3. Confirm the document got linked to the real leave_request_id.
        docs = leave_service.list_leave_documents(request_id)
        print("3. list_leave_documents:", docs)
        assert len(docs["documents"]) == 1
        assert docs["documents"][0]["s3Key"] == doc["s3Key"]

        # 4. Confirm it shows up in the employee's own "My Requests" view, PENDING.
        my_requests_before = leave_service.list_my_leave_requests("EMP052")
        mine = next(r for r in my_requests_before["requests"] if r["requestId"] == request_id)
        print("4. list_my_leave_requests (before resolve):", mine)
        assert mine["status"] == "PENDING"
        assert mine["decision"] is None
        assert mine["hrSpecialistEmployeeId"] is None

        # 5. Resolve as a real HR specialist persona, with their employee_id.
        resolve_result = hitl_service.resolve_hitl_request(
            hitl_request_id=hitl_request_id,
            decision="APPROVED",
            response_text="Approved - documentation checks out.",
            resolved_by="Daniel Rodriguez",
            resolved_by_employee_id="EMP021",
        )
        print("5. resolve_hitl_request:", resolve_result)
        assert resolve_result["employeeEmail"], "employeeEmail must be present for the notification step"

        # 6. Confirm the review row now shows the real specialist + decision.
        my_requests_after = leave_service.list_my_leave_requests("EMP052")
        mine_after = next(r for r in my_requests_after["requests"] if r["requestId"] == request_id)
        print("6. list_my_leave_requests (after resolve):", mine_after)
        assert mine_after["status"] == "COMPLETED"
        assert mine_after["decision"] == "APPROVED"
        assert mine_after["hrSpecialistEmployeeId"] == "EMP021"
        assert mine_after["hrSpecialistName"] == "Daniel Rodriguez"
        assert mine_after["respondedAt"] is not None

        print("\nALL PHASE 165 LIVE CHECKS PASSED")
    finally:
        db.close()


if __name__ == "__main__":
    main()
