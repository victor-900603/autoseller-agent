import time

import pytest

from core.brain.llm_gateway import (
    GatewayError,
    MockProvider,
    create_gateway,
    get_provider,
)


def test_mock_generate_deterministic():
    gateway = create_gateway("mock")
    assert gateway.generate("listing.title", {"brand": "Logitech"}) == "[mock:listing.title]"


def test_mock_analyze_counts_images():
    gateway = create_gateway("mock")
    assert gateway.analyze("vision.item", ["a.jpg", "b.jpg"]) == "[mock:vision.item:2images]"


def test_unknown_provider_rejected():
    with pytest.raises(GatewayError):
        get_provider("unknown-vendor")


def test_provider_failure_wrapped():
    class BrokenProvider:
        def generate(self, prompt_id, params):
            raise RuntimeError("boom")

        def analyze(self, prompt_id, images, params):
            raise RuntimeError("boom")

    gateway = create_gateway("mock")
    gateway._provider = BrokenProvider()
    with pytest.raises(GatewayError):
        gateway.generate("listing.title")


def test_timeout_surfaces_as_gateway_error():
    class SlowProvider(MockProvider):
        def generate(self, prompt_id, params):
            time.sleep(5)
            return "late"

    gateway = create_gateway("mock", timeout_seconds=1)
    gateway._provider = SlowProvider()
    with pytest.raises(GatewayError, match="超時"):
        gateway.generate("listing.title")
