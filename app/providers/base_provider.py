from abc import ABC, abstractmethod
from typing import Dict, Any
from fastapi.responses import StreamingResponse, JSONResponse

class BaseProvider(ABC):
    @abstractmethod
    async def chat_completion(self, request_data: Dict[str, Any]) -> StreamingResponse:
        pass

    @abstractmethod
    async def get_models(self) -> JSONResponse:
        pass
