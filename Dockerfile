FROM node:20-alpine AS frontend-build

WORKDIR /app

# Install pnpm globally
RUN npm install -g pnpm

# Copy package files first for better caching
COPY frontend/package.json frontend/pnpm-lock.yaml ./

# Install dependencies (cached if package.json doesn't change)
RUN pnpm install --frozen-lockfile

# Copy frontend source code
COPY frontend/ .

# Build frontend
RUN pnpm run build

# Backend build stage
FROM python:3.13-slim AS backend-build

RUN pip install uv

WORKDIR /app

# Copy dependency files first for better caching
COPY backend/pyproject.toml backend/uv.lock ./

# Install Python dependencies (cached if pyproject.toml/uv.lock don't change)
RUN uv sync --frozen --no-install-project

# Now copy the backend source code
COPY backend/ ./backend/

# Create __init__.py files for all directories containing Python files
RUN find backend/ -name "*.py" -exec dirname {} \; | xargs -I {} touch {}/__init__.py

# Copy frontend build to backend static directory
COPY --from=frontend-build /app/dist ./static

# Activate virtual environment
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV PYTHONPATH=/app/backend

# Expose port
EXPOSE 5611

# Set working directory for the app
WORKDIR /app/backend

# Start the application
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5611"]
