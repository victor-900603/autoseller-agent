import concurrent.futures
from typing import Protocol


class GatewayError(Exception):
    pass


class ModelProvider(Protocol):
    def generate(self, prompt_id: str, params: dict) -> str:
        ...

    def analyze(self, prompt_id: str, images: list[str], params: dict) -> str:
        ...


class MockProvider:
    def generate(self, prompt_id: str, params: dict) -> str:
        return f"[mock:{prompt_id}]"

    def analyze(self, prompt_id: str, images: list[str], params: dict) -> str:
        return f"[mock:{prompt_id}:{len(images)}images]"


class LlmGateway:
    def __init__(self, provider: ModelProvider, timeout_seconds: int = 30) -> None:
        self._provider = provider
        self._timeout_seconds = timeout_seconds

    @property
    def timeout_seconds(self) -> int:
        return self._timeout_seconds

    def generate(self, prompt_id: str, params: dict | None = None) -> str:
        try:
            return self._call(self._provider.generate, prompt_id, params or {})
        except GatewayError:
            raise
        except Exception as exc:
            raise GatewayError(f"generate 失敗：{prompt_id}") from exc

    def analyze(self, prompt_id: str, images: list[str], params: dict | None = None) -> str:
        try:
            return self._call(self._provider.analyze, prompt_id, images, params or {})
        except GatewayError:
            raise
        except Exception as exc:
            raise GatewayError(f"analyze 失敗：{prompt_id}") from exc

    def _call(self, func, *args):
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(func, *args)
            try:
                return future.result(timeout=self._timeout_seconds)
            except concurrent.futures.TimeoutError as exc:
                raise GatewayError("模型回應超時") from exc


def get_provider(name: str) -> ModelProvider:
    if name == "mock":
        return MockProvider()
    raise GatewayError(f"未知供應器：{name}")


def create_gateway(provider_name: str = "mock", timeout_seconds: int = 30) -> LlmGateway:
    return LlmGateway(get_provider(provider_name), timeout_seconds)
