"""Entry point for Language Conversation Coach CLI."""
import warnings
import os
warnings.filterwarnings("ignore", module="urllib3")
os.environ['HF_HUB_DISABLE_PROGRESS_BARS'] = '1'

# Only force offline mode if the MLX model cache directory exists
model_cache_dir = os.path.expanduser('~/.cache/huggingface/hub/models--mlx-community--Qwen2.5-7B-Instruct-4bit')
if os.path.exists(model_cache_dir):
    os.environ['HF_HUB_OFFLINE'] = '1'

import sys
from app.cli import main
from app.llm import DEBUG

if __name__ == '__main__':
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print("\nExiting...")
        sys.exit(0)
    except Exception as e:
        # DEBUG must reach the developer. app/cli.py re-raises under DEBUG at
        # three call sites precisely so a traceback survives; catching bare
        # Exception here swallowed every one of them, and README documents
        # `DEBUG=1 python3 main.py` as the way to debug. With the flag set that
        # produced LESS than with it unset — one line, no traceback, and the
        # word "startup" even for a failure raised mid-session (OPEN-33).
        if DEBUG:
            raise
        print(f"\n[⚠️ Error: {e}]")
        sys.exit(1)