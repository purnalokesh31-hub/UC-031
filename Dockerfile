# ==============================================================================
# CropGuard AI (UC-031) — Production Container for Google Cloud Run
# Multi-stage build: Vite React SPA + FastAPI ML Engine (ONNX + Scikit-Learn)
# ==============================================================================

# ── Stage 1: Build Frontend Assets ────────────────────────────────────────── #
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ── Stage 2: Production Python Runtime ────────────────────────────────────── #
FROM python:3.12-slim AS runner
WORKDIR /app

# Install runtime system libraries (libgomp for ONNX Runtime & Scikit-Learn OpenMP)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Optimize Python runtime for containers
ENV PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

# Install Python requirements
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r ./backend/requirements.txt

# Copy backend application, models, databases, and research datasets
COPY backend/ ./backend/
COPY research/ ./research/

# Copy built frontend distribution from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Expose standard Cloud Run container port
EXPOSE 8080

# Start Uvicorn bound to 0.0.0.0 and dynamic $PORT injected by Cloud Run
CMD ["sh", "-c", "exec uvicorn main:app --app-dir backend --host 0.0.0.0 --port ${PORT:-8080}"]
