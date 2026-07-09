import pytest
from services.orchestrator_service.nlp.feedback_filter import FeedbackFilter
from services.orchestrator_service.domain.models import Message

def test_feedback_filter_match_feedback_arabic():
    ff = FeedbackFilter()
    
    # Test valid Arabic feedback matches
    res1 = ff.match_feedback("ممتاز")
    assert res1 is not None
    assert any(res1 == opt for opt in ff._arabic_responses)

    res2 = ff.match_feedback("واضح جداً")  # normalized should match "واضح جدا"
    assert res2 is not None
    assert any(res2 == opt for opt in ff._arabic_responses)

    # Test invalid matches
    assert ff.match_feedback("ما هي سياسة السفر؟") is None
    assert ff.match_feedback("") is None

def test_feedback_filter_match_feedback_english():
    ff = FeedbackFilter()
    
    # Test valid English feedback matches
    res1 = ff.match_feedback("ok")
    assert res1 is not None
    assert any(res1 == opt for opt in ff._english_responses)

    res2 = ff.match_feedback("Awesome!!")
    assert res2 is not None
    assert any(res2 == opt for opt in ff._english_responses)

    # Test invalid matches
    assert ff.match_feedback("show me salary slip") is None

def test_feedback_filter_question_bypass():
    ff = FeedbackFilter()
    
    # Assistant asked a question:
    history = [
        Message(role="user", content="طلب إجازة سنوية"),
        Message(role="assistant", content="هل تريد تأكيد طلب الإجازة؟")
    ]
    
    # Simple confirmation words like "نعم" or "لا" or "موافق" or "ok" must bypass the filter (return None)
    assert ff.match_feedback("نعم", history) is None
    assert ff.match_feedback("موافق", history) is None
    assert ff.match_feedback("لا", history) is None
    assert ff.match_feedback("ok", history) is None
    assert ff.match_feedback("yes", history) is None
    assert ff.match_feedback("no", history) is None

    # Feedback like "ممتاز" should still be handled normally
    res = ff.match_feedback("ممتاز", history)
    assert res is not None

def test_feedback_filter_match_followup_dynamic():
    ff = FeedbackFilter()
    
    # Setup history where the assistant mentioned "50%" and "انتداب"
    history = [
        Message(role="user", content="ما هي تفاصيل بدل السكن؟"),
        Message(role="assistant", content="وفقاً لسياسة السفر، يتم تغطية الإقامة ويصرف 50% من المصروف اليومي كـ انتداب.")
    ]
    
    # 1. Matches keyword "انتداب"
    rewritten1 = ff.match_followup("انتداب؟", history)
    assert rewritten1 is not None
    assert "انتداب" in rewritten1
    assert "سياسة السفر" in rewritten1  # Contains assistant message context

    # 2. Matches "50%"
    rewritten2 = ff.match_followup("50% ؟", history)
    assert rewritten2 is not None
    assert "50%" in rewritten2
    assert "سياسة السفر" in rewritten2  # Contains assistant message context

    # 3. No match when keyword/value is not in assistant response (and not a particle)
    assert ff.match_followup("طعام؟", history) is None
    
    # 4. Matches particle "لماذا؟" even if not in the previous response
    rewritten3 = ff.match_followup("لماذا؟", history)
    assert rewritten3 is not None
    assert "لماذا" in rewritten3
    assert "سياسة السفر" in rewritten3  # Contains assistant message context

def test_feedback_filter_no_question_feedback():
    ff = FeedbackFilter()
    
    # Assistant did NOT ask a question:
    history = [
        Message(role="user", content="ما هي سياسة السفر؟"),
        Message(role="assistant", content="يتم تغطية الإقامة ويصرف 50% كـ انتداب.")
    ]
    
    # "نعم" or "yes" when there is no question should return a polite acknowledgement response
    res1 = ff.match_feedback("نعم", history)
    assert res1 is not None
    assert any(res1 == opt for opt in ff._arabic_responses)

    res2 = ff.match_feedback("yes", history)
    assert res2 is not None
    assert any(res2 == opt for opt in ff._english_responses)

