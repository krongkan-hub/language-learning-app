# Web front end only. Builds `app.web:serve` (FastAPI/uvicorn) for a
# container. It does NOT run local MLX inference — see docs/DEPLOYMENT.md
# for exactly what does and does not work today, and why.
# Stage 1: build the React front end (frontend/ -> app/static/ui).
FROM node:22-slim AS ui
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build -- --outDir /ui

FROM python:3.11-slim

WORKDIR /app

# pyproject.toml declares readme = "README.md"; setuptools reads that file
# during the build, so it has to be in the build context even though nothing
# at runtime touches it.
COPY pyproject.toml README.md ./
COPY main.py ./
COPY app ./app
COPY --from=ui /ui ./app/static/ui

# `mlx-lm` is a base dependency (pyproject.toml [project].dependencies), but
# mlx-lm's own metadata only requires Apple's `mlx` package
# "; platform_system == 'Darwin'" — so this installs cleanly on this Linux
# image without ever attempting to fetch the Metal-only `mlx` wheel. That
# does NOT mean the app can run: see docs/DEPLOYMENT.md — importing
# app.web still fails today, because mlx_lm imports `mlx.core`
# unconditionally the moment it is imported.
RUN pip install --no-cache-dir .

# The database is PostgreSQL with pgvector (app/db/). The DSN points at the
# `db` service in docker-compose.yml; override it to use any other server.
ENV LANGUAGE_COACH_DSN="host=db dbname=language_coach user=coach password=coach"

EXPOSE 8000

# Runs from /app rather than from the installed package. It used to HAVE to:
# pyproject.toml declared no package-data, so `pip install .` dropped every
# non-.py file — the 80 scenarios and the web page included. That is fixed
# (see docs/DEPLOYMENT.md), and running from the source tree is now just the
# simpler thing to mount over.
#
# host='0.0.0.0' (serve()'s own default is 127.0.0.1, loopback-only, which
# would be unreachable from outside this container).
CMD ["python", "-c", "from app.web import serve; serve(host='0.0.0.0', port=8000)"]
