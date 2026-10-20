import pytest
from django.contrib.contenttypes.models import ContentType


@pytest.fixture(autouse=True)
def clear_content_type_cache():
    ContentType.objects.clear_cache()
    yield
    ContentType.objects.clear_cache()
