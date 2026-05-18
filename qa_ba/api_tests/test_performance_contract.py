from __future__ import annotations

from backend.app.services.answer_service import contains_suspicious_foreign_fragment, is_cacheable_institutional_query


def test_answer_cache_does_not_cache_personal_queries() -> None:
    assert not is_cacheable_institutional_query(query="hôm nay tôi cần làm gì", include_memory=False, memory_context=None)
    assert not is_cacheable_institutional_query(query="tôi có task nào chưa xong", include_memory=False, memory_context=None)
    assert is_cacheable_institutional_query(query="hiệu trưởng HUS là ai", include_memory=False, memory_context=None)


def test_suspicious_foreign_language_output_is_detected() -> None:
    answer = "Khoa học dữ liệu có terming dari teknologi, sains bumi dan kehidupan."

    assert contains_suspicious_foreign_fragment(answer.lower())

