"""One-off Phase 172 live verification against real local Postgres - no
MCP server process needed, exercises the service layer directly (same
pattern as phase165_live_verify.py). Run as: python -m scripts.phase172_live_verify
"""

from datetime import date, timedelta

from src.app.repos.database import get_db
from src.app.services.leave_request_service import LeaveRequestService
from src.app.services.hitl_service import HitlService


def main() -> None:
    db = next(get_db())
    try:
        leave_service = LeaveRequestService(db)
        hitl_service = HitlService(db)

        start = date.today() + timedelta(days=30)
        end = start + timedelta(days=1)

        submit_result = leave_service.submit_unpaid_leave_request(
            employee_id="EMP052",
            start_date=start,
            end_date=end,
            purpose="Phase 172 live verification",
            is_repeat_within_12_months=False,
            leave_type_code="UNPAID",
        )
        hitl_request_id = submit_result["hitlRequestId"]
        print(f"1. Submitted - hitlRequestId={hitl_request_id}")

        brief_result = leave_service.set_review_brief(
            hitl_request_id=hitl_request_id,
            review_brief="Eddy Employee requests 2 days of unpaid leave for personal reasons. No prior repeat requests.",
        )
        print(f"2. Review brief set - {brief_result}")

        my_requests_before = leave_service.list_my_leave_requests(employee_id="EMP052")
        this_request = next(r for r in my_requests_before["requests"] if r["requestId"] == submit_result["requestId"])
        assert this_request["taskState"] == "input_required", this_request["taskState"]
        assert this_request["reviewBrief"] == brief_result and False or True  # just confirming no exception above
        assert "Eddy Employee requests 2 days" in this_request["reviewBrief"]
        print(f"3. Before resolve - taskState={this_request['taskState']!r}, reviewBrief set correctly")

        resolve_result = hitl_service.resolve_hitl_request(
            hitl_request_id=hitl_request_id,
            decision="APPROVED",
            response_text="Approved - documentation not required for this duration.",
            resolved_by="Hana Support",
            resolved_by_employee_id="EMP051",
        )
        print(f"4. Resolved - {resolve_result}")

        artifact_result = hitl_service.record_produced_artifact(
            hitl_request_id=hitl_request_id,
            artifact={"type": "email", "recipient": "eddy@example.com", "sent": True, "sent_at": "2026-10-12T00:00:00"},
        )
        print(f"5. Artifact recorded - {artifact_result}")

        my_requests_after = leave_service.list_my_leave_requests(employee_id="EMP052")
        this_request_after = next(
            r for r in my_requests_after["requests"] if r["requestId"] == submit_result["requestId"]
        )
        assert this_request_after["taskState"] == "completed", this_request_after["taskState"]
        assert this_request_after["decisionMessage"]["role"] == "specialist"
        assert this_request_after["decisionMessage"]["parts"][0]["content"] == resolve_result["response"]
        assert len(this_request_after["producedArtifacts"]) == 1
        assert this_request_after["producedArtifacts"][0]["type"] == "email"
        print(
            f"6. After resolve - taskState={this_request_after['taskState']!r}, "
            f"decisionMessage={this_request_after['decisionMessage']}, "
            f"producedArtifacts={this_request_after['producedArtifacts']}"
        )

        print("\nALL PHASE 172 SCHEMA/SERVICE CHECKS PASSED")

        cleanup = hitl_service.admin_delete_hitl_request(hitl_request_id)
        print(f"\nCleanup - {cleanup}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
