FROM python:3.12-slim
RUN pip install uv
WORKDIR /app
COPY pyproject.toml .
RUN uv pip install --system -e ".[dev]"
COPY . .
EXPOSE 8000
ENV PYTHONUNBUFFERED=1
CMD ["uv", "run", "chainlit", "run", "src/ea_workbench/chat/app.py", "--host", "0.0.0.0", "--port", "8000"]
