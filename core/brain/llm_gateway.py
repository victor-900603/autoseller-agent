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
        """樁回覆，內容僅供測試識別。"""
        return f"[mock:{prompt_id}]"

    def analyze(self, prompt_id: str, images: list[str], params: dict) -> str:
        """樁回覆，標示圖片數量供測試識別。"""
        return f"[mock:{prompt_id}:{len(images)}images]"


class LlmGateway:
    def __init__(self, provider: ModelProvider, timeout_seconds: int = 30) -> None:
        """注入供應器與超時秒數，超時由呼叫轉為網關錯誤。"""
        self._provider = provider
        self._timeout_seconds = timeout_seconds

    @property
    def timeout_seconds(self) -> int:
        return self._timeout_seconds

    def generate(self, prompt_id: str, params: dict | None = None) -> str:
        """經超時包裝呼叫文字生成，失敗統一轉網關錯誤。"""
        try:
            return self._call(self._provider.generate, prompt_id, params or {})
        except GatewayError:
            raise
        except Exception as exc:
            raise GatewayError(f"generate 失敗：{prompt_id}") from exc

    def analyze(self, prompt_id: str, images: list[str], params: dict | None = None) -> str:
        """經超時包裝呼叫圖片理解，失敗統一轉網關錯誤。"""
        try:
            return self._call(self._provider.analyze, prompt_id, images, params or {})
        except GatewayError:
            raise
        except Exception as exc:
            raise GatewayError(f"analyze 失敗：{prompt_id}") from exc

    def _call(self, func, *args):
        """單執行緒執行並限時等待，超時轉網關錯誤。"""
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(func, *args)
            try:
                return future.result(timeout=self._timeout_seconds)
            except concurrent.futures.TimeoutError as exc:
                raise GatewayError("模型回應超時") from exc


def get_provider(name: str) -> ModelProvider:
    """依名稱路由供應器，未知名稱直接拋錯。"""
    if name == "mock":
        return MockProvider()
    raise GatewayError(f"未知供應器：{name}")


def create_gateway(provider_name: str = "mock", timeout_seconds: int = 30) -> LlmGateway:
    """組裝網關入口，預設 mock 供應器。"""
    return LlmGateway(get_provider(provider_name), timeout_seconds)
