import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def test_source_class_defined_in_models():
    from models import Source

    assert Source.__tablename__ == "sources"
    assert hasattr(Source, "name")
    assert hasattr(Source, "url")
    assert hasattr(Source, "category")
    assert hasattr(Source, "is_validated")
    assert hasattr(Source, "ping_failures_count")


def test_source_still_importable_from_source_registry():
    from source_registry import Source

    assert Source.__tablename__ == "sources"
