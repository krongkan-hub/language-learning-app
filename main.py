"""Entry point for Language Conversation Coach CLI."""
import warnings
import os
warnings.filterwarnings("ignore", module="urllib3")
os.environ['HF_HUB_DISABLE_PROGRESS_BARS'] = '1'

# Only force offline mode if the MLX model cache directory exists
model_cache_dir = os.path.expanduser('~/.cache/huggingface/hub/models--mlx-community--Qwen2.5-7B-Instruct-4bit')
if os.path.exists(model_cache_dir):
    os.environ['HF_HUB_OFFLINE'] = '1'

from app.cli import main

if __name__ == '__main__':
    main()