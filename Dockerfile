# Web front end only. Builds `app.web:serve` (FastAPI/uvicorn) for a
# container. It does NOT run local MLX inference — see docs/DEPLOYMENT.md
# for exactly what does and does not work today, and why.
FROM python:3.11-slim

WORKDIR /app

# pyproject.toml declares readme = "README.md"; setuptools reads that file
# during the build, so it has to be in the build context even though nothing
# at runtime touches it.
COPY pyproject.toml README.md ./
COPY main.py ./
COPY app ./app

# `mlx-lm` is a base dependency (pyproject.toml [project].dependencies), but
# mlx-lm's own metadata only requires Apple's `mlx` package
# "; platform_system == 'Darwin'" — so this installs cleanly on this Linux
# image without ever attempting to fetch the Metal-only `mlx` wheel. That
# does NOT mean the app can run: see docs/DEPLOYMENT.md — importing
# app.web still fails today, because mlx_lm imports `mlx.core`
# unconditionally the moment it is imported.
RUN pip install --no-cache-dir .[web]

# app/db.py reads LANGUAGE_COACH_DB and falls back to ~/.language-coach/
# otherwise, which is not a sensible place inside a container.
ENV LANGUAGE_COACH_DB=/data/sessions.db
VOLUME ["/data"]

EXPOSE 8000

# Runs from /app, not the installed wheel: pyproject.toml declares no
# package-data, so `pip install .` silently drops every non-.py file —
# app/scenarios/data/*.json (80 scenarios) and app/static/index.html
# included (verified locally; see docs/DEPLOYMENT.md). Python resolves
# `import app` against this working directory ahead of site-packages, so
# running from source here keeps those files instead of losing them.
#
# host='0.0.0.0' (serve()'s own default is 127.0.0.1, loopback-only, which
# would be unreachable from outside this container).
CMD ["python", "-c", "from app.web import serve; serve(host='0.0.0.0', port=8000)"]
