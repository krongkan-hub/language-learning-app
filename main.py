import warnings
import os
warnings.filterwarnings("ignore", module="urllib3")
os.environ['HF_HUB_DISABLE_PROGRESS_BARS'] = '1'
os.environ['HF_HUB_OFFLINE'] = '1'

from app.cli import main

if __name__ == '__main__':
    main()