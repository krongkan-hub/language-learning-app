"""Start Language Coach: the web app on http://127.0.0.1:8000.

    python3 main.py            # or: make web
    DEBUG=1 python3 main.py    # full tracebacks

The command-line front end was retired on 2026-09-26; the browser is now the
only way in, and everything it needs is in app/web.py.
"""
import os
import warnings

warnings.filterwarnings("ignore", module="urllib3")
os.environ['HF_HUB_DISABLE_PROGRESS_BARS'] = '1'

# Only force offline mode if the MLX model cache directory exists
model_cache_dir = os.path.expanduser(
    '~/.cache/huggingface/hub/models--mlx-community--Qwen2.5-7B-Instruct-4bit')
if os.path.exists(model_cache_dir):
    os.environ['HF_HUB_OFFLINE'] = '1'

from app.web import serve  # noqa: E402  (after the environment is set)

if __name__ == '__main__':
    serve()
