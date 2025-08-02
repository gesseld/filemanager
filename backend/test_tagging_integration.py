from services.tagging import TaggingService

def test_tagging():
    """Test the tagging service with sample text"""
    service = TaggingService()
    sample_text = "Artificial Intelligence is transforming banking and finance sectors."
    tags = service.auto_tag(sample_text)
    print("Generated tags:", tags)
    assert isinstance(tags, list), "Tags should be a list"
    assert len(tags) > 0, "Should generate at least one tag"

if __name__ == "__main__":
    test_tagging()