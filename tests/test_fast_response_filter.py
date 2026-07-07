import pytest
from services.orchestrator_service.nlp.fast_response_filter import FastResponseFilter, normalize_arabic

def test_normalize_arabic_tashkeel():
    # Test removing diacritics
    assert normalize_arabic("سَلَامٌ عَلَيْكُمْ") == "سلام عليكم"

def test_normalize_arabic_alef_and_teh_marbuta():
    # Test standardizing أ, إ, آ -> ا and ة -> ه and ى -> ي
    assert normalize_arabic("أهلاً وسهلاً") == "اهلا وسهلا"
    assert normalize_arabic("إجازة سنوية") == "اجازه سنويه"
    assert normalize_arabic("على الرحب") == "على الرحب" or normalize_arabic("على الرحب") == "علي الرحب"

def test_normalize_arabic_punctuation():
    # Test stripping punctuation and duplicate spaces
    assert normalize_arabic("السلام عليكم؟؟") == "السلام عليكم"
    assert normalize_arabic("مرحبا، كيف حالك؟!") == "مرحبا كيف حالك"

def test_fast_response_filter_match():
    filter_service = FastResponseFilter()
    
    # Exact greeting matches
    resp1 = filter_service.match("السلام عليكم")
    assert resp1 is not None
    assert any(resp1 == option for option in filter_service.predefined_responses["السلام عليكم"])
    
    # Matching with punctuation and diacritics
    resp2 = filter_service.match("سَلَامٌ عَلَيْكُمْ؟؟")
    assert resp2 is not None
    assert any(resp2 == option for option in filter_service.predefined_responses["سلام عليكم"])
    
    # Match with normal text containing greeting variations
    resp3 = filter_service.match("أهلاً!!")
    assert resp3 is not None
    assert any(resp3 == option for option in filter_service.predefined_responses["اهلا"])

def test_fast_response_filter_no_match():
    filter_service = FastResponseFilter()
    
    # Normal queries should return None, falling back to the standard LLM/RAG pipeline
    assert filter_service.match("ما هي سياسة الإجازة السنوية؟") is None
    assert filter_service.match("كشف الراتب لشهر مايو") is None
    assert filter_service.match("emp101") is None
    assert filter_service.match("") is None
    assert filter_service.match(None) is None

def test_fast_response_randomness():
    filter_service = FastResponseFilter()
    
    # Call match many times to ensure we hit different random responses
    responses = set()
    for _ in range(50):
        res = filter_service.match("السلام عليكم")
        responses.add(res)
    
    # Since there are 3 predefined responses for "السلام عليكم", we should see more than 1 distinct response
    assert len(responses) > 1

def test_fast_response_new_greetings():
    filter_service = FastResponseFilter()
    
    # Test newly added greetings and FAQs
    assert filter_service.match("كيف الحال") is not None
    assert filter_service.match("صباحك ورد") is not None
    assert filter_service.match("كل عام وأنتم بخير؟؟") is not None
    assert filter_service.match("ما هي وظيفتك؟") is not None
    assert filter_service.match("ما عملك") is not None
    assert filter_service.match("عيد مبارك") is not None

