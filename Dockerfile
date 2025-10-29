# ====================================================================
# Dockerfile for googletranslate-2api (v1.0 - Chimera Synthesis)
# ====================================================================

FROM python:3.10-slim

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建并切换到非 root 用户
RUN useradd --create-home appuser && \
    chown -R appuser:appuser /app
USER appuser

# 暴露端口并启动
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
