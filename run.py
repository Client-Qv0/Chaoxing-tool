"""超星学习通自动刷课 - 程序入口。

直接运行此文件启动 CLI 交互程序。
"""

import sys
from pathlib import Path

if __name__ == "__main__" and __package__ is None:
    this_file = Path(__file__).resolve()
    root_dir = this_file.parent.parent  # 定位到 "超星学习通" 文件夹
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))
    __package__ = "py"

from .main import main

if __name__ == '__main__':
    main()