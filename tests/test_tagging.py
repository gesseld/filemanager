import pytest
from backend.services.tagging import TaggingService

@pytest.fixture
def tagging_service():
    return TaggingService()

def test_auto_tag_returns_list(tagging_service):
    """Test that auto_tag returns a list of strings"""
    result = tagging_service.auto_tag("This is about AI and Finance")
    assert isinstance(result, list)
    assert all(isinstance(tag, str) for tag in result)

def test_auto_tag_contains_expected_tags(tagging_service):
    """Test that expected tags are returned for known inputs"""
    result = tagging_service.auto_tag("Artificial Intelligence in banking")
    assert "AI" in result
    assert "Finance" in result