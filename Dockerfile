FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY relatorio_dns ./relatorio_dns
RUN uv sync --frozen --no-dev
ENV PATH="/app/.venv/bin:$PATH"
ENTRYPOINT ["relatorio-dns"]
CMD ["--help"]
