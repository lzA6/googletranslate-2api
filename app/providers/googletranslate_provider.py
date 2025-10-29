import httpx
import json
import time
import uuid
import re
from typing import Dict, Any, AsyncGenerator, Optional

from fastapi import HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from loguru import logger
from markdownify import markdownify as md
from bs4 import BeautifulSoup

from app.core.config import settings
from app.providers.base_provider import BaseProvider
from app.utils.sse_utils import create_sse_data, create_chat_completion_chunk, DONE_CHUNK

class GoogleTranslateProvider(BaseProvider):
    BASE_URL = "https://translate-pa.googleapis.com/v1/translateHtml"
    CHINESE_REGEX = re.compile(r'[\u4e00-\u9fa5]')

    def __init__(self):
        self.client: Optional[httpx.AsyncClient] = None

    async def initialize(self):
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY 未在 .env 文件中配置。")
        self.client = httpx.AsyncClient(timeout=settings.API_REQUEST_TIMEOUT)

    async def close(self):
        if self.client:
            await self.client.aclose()

    async def chat_completion(self, request_data: Dict[str, Any]) -> StreamingResponse:
        
        async def stream_generator() -> AsyncGenerator[bytes, None]:
            request_id = f"chatcmpl-{uuid.uuid4()}"
            model_name = request_data.get("model", settings.DEFAULT_MODEL)
            
            try:
                headers = self._prepare_headers()
                payload = self._prepare_payload(request_data)
                
                logger.info(f"向上游发送翻译请求: {payload}")
                
                response = await self.client.post(self.BASE_URL, headers=headers, json=payload)
                
                logger.info(f"上游响应状态码: {response.status_code}")
                response.raise_for_status()
                
                response_data = response.json()
                logger.info(f"收到上游响应: {response_data}")

                # --- 健壮的响应解析逻辑 (已修改) ---
                translated_html = ""
                if isinstance(response_data, list) and response_data:
                    if isinstance(response_data[0], list) and response_data[0]:
                        # 正常情况，获取翻译后的 HTML
                        translated_html = response_data[0][0]
                elif not isinstance(response_data, list):
                    # 如果响应不是列表，则为异常情况
                    raise ValueError(f"上游响应格式不符合预期: {response_data}")
                # 如果 response_data 是空列表 `[]`，则 translated_html 保持为空字符串，这是正常情况

                # --- 增强的文本清理 ---
                soup = BeautifulSoup(translated_html, 'html.parser')
                clean_text = soup.get_text()
                # 移除零宽空格等不可见字符
                clean_text = clean_text.replace('\u200b', '')

                # 将清理后的文本转换为 Markdown
                markdown_text = md(clean_text)

                # 发送包含完整翻译结果的单个数据块
                chunk = create_chat_completion_chunk(request_id, model_name, markdown_text)
                yield create_sse_data(chunk)
                
                # 发送结束标志
                final_chunk = create_chat_completion_chunk(request_id, model_name, "", "stop")
                yield create_sse_data(final_chunk)
                yield DONE_CHUNK

            except Exception as e:
                logger.error(f"处理翻译请求时发生错误: {e}", exc_info=True)
                error_message = f"内部服务器错误: {str(e)}"
                error_chunk = create_chat_completion_chunk(request_id, model_name, error_message, "stop")
                yield create_sse_data(error_chunk)
                yield DONE_CHUNK

        return StreamingResponse(stream_generator(), media_type="text/event-stream")

    def _prepare_headers(self) -> Dict[str, str]:
        # (已修改) 添加了 User-Agent 来模拟真实浏览器请求
        return {
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Content-Type": "application/json+protobuf",
            "Origin": "https://stackoverflow.ai",
            "Referer": "https://stackoverflow.ai/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
            "x-goog-api-key": settings.GOOGLE_API_KEY,
        }

    def _prepare_payload(self, request_data: Dict[str, Any]) -> list:
        messages = request_data.get("messages", [])
        if not messages or messages[-1].get("role") != "user":
            raise HTTPException(status_code=400, detail="请求中缺少有效的用户消息。")
        
        content = messages[-1]["content"]
        # 如果 content 为空或 None，API 可能会返回错误或空内容，这里我们将其视为空字符串
        text_to_translate = content if content is not None else ""
        
        # 智能语言路由逻辑
        source_lang = request_data.get("source_lang", "auto")
        target_lang = request_data.get("target_lang")

        if not target_lang:
            # 如果用户未指定目标语言，则自动判断
            if self.CHINESE_REGEX.search(text_to_translate):
                target_lang = "en" # 输入是中文，默认翻译成英文
                logger.info("检测到中文输入，自动设置目标语言为 'en'")
            else:
                target_lang = "zh-CN" # 输入是其他语言，默认翻译成中文
                logger.info("未检测到中文输入，自动设置目标语言为 'zh-CN'")
        
        return [
            [[text_to_translate], source_lang, target_lang],
            "te_lib"
        ]

    async def get_models(self) -> JSONResponse:
        model_data = {
            "object": "list",
            "data": [
                {"id": name, "object": "model", "created": int(time.time()), "owned_by": "lzA6"}
                for name in settings.KNOWN_MODELS
            ]
        }
        return JSONResponse(content=model_data)
