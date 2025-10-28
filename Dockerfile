FROM python:3.13-slim

# Install uv
RUN pip install uv

# Set workdir
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-install-project

# Copy source
COPY . .

# Expose port
EXPOSE 8000

# Run
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]