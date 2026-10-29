FROM node:24-alpine AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 AEGIS_HOST=0.0.0.0 AEGIS_DB=/app/data/aegis.db
WORKDIR /app
RUN groupadd -g 10001 aegis && useradd -u 10001 -g aegis aegis && mkdir data && chown aegis:aegis data
COPY --chown=aegis:aegis backend/ backend/
RUN python -m pip install --no-cache-dir -r backend/requirements-ai.txt
COPY --from=frontend /build/dist frontend/dist
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/health',timeout=2)"
CMD ["python", "backend/server.py"]
