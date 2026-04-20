from app.api.schemas import ComplaintPatchBody
from shared.enums import ComplaintStatus as CS


def test_complaint_patch_body_reopen_pending_accepts_empty_strings():
    m = ComplaintPatchBody.model_validate(
        {"status": CS.PENDING, "rating": "", "resident_feedback": ""}
    )
    assert m.status == CS.PENDING
    assert m.rating is None
    assert m.resident_feedback is None


def test_complaint_patch_body_completion_accepts_empty_feedback():
    m = ComplaintPatchBody.model_validate({"rating": 4, "resident_feedback": ""})
    assert m.rating == 4
    assert m.resident_feedback is None


def test_complaint_patch_body_status_strips_whitespace():
    m = ComplaintPatchBody.model_validate({"status": "  pending  "})
    assert m.status == CS.PENDING


def test_complaint_patch_body_resident_edit_fields():
    m = ComplaintPatchBody.model_validate(
        {
            "category": "electrical",
            "priority": "high",
            "description": "Updated description text",
        }
    )
    assert m.category.value == "electrical"
    assert m.priority.value == "high"
    assert m.description == "Updated description text"
