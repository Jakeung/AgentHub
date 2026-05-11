FROM node:20-alpine AS frontend-builder
WORKDIR /app
COPY web/package.json web/package-lock.json* ./
RUN npm ci --registry=https://registry.npmmirror.com
COPY web/ .
RUN npm run build

FROM python:3.10-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl gosu && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
COPY backend/ .
COPY --from=frontend-builder /app/dist /app/static
RUN mkdir -p /app/data && \
    adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
COPY backend/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
