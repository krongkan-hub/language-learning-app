"""Start Language Coach on the command line.

    python3 main.py                  # or: make run
    python3 main.py --lang Japanese  # skip the language question
    python3 main.py --stats          # progress report, no model needed
    DEBUG=1 python3 main.py          # full tracebacks
"""
import os
import sys
import warnings

warnings.filterwarnings("ignore", module="urllib3")
os.environ['HF_HUB_DISABLE_PROGRESS_BARS'] = '1'

# Only force offline mode if the MLX model cache directory exists
model_cache_dir = os.path.expanduser(
    '~/.cache/huggingface/hub/models--mlx-community--Qwen2.5-7B-Instruct-4bit')
if os.path.exists(model_cache_dir):
    os.environ['HF_HUB_OFFLINE'] = '1'

from app.cli import main  # noqa: E402  (after the environment is set)
from app.llm import DEBUG  # noqa: E402

if __name__ == '__main__':
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print("\nExiting...")
        sys.exit(0)
    except Exception as e:
        # Under DEBUG the traceback must reach the developer; catching bare
        # Exception here once swallowed every one of them (OPEN-33).
        if DEBUG:
            raise
        print(f"\n[⚠️ Error: {e}]")
        sys.exit(1)
