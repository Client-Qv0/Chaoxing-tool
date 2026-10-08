"""超星学习通自动刷课 - 程序入口。

直接运行此文件启动 CLI 交互程序。
"""

import sys
from pathlib import Path

if __name__ == "__main__" and __package__ is None:
    this_file = Path(__file__).resolve()
    root_dir = this_file.parent.parent  # 上级目录，作为包的搜索路径
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))
    __package__ = this_file.parent.name  # 目录名即包名，仓库被改名/换目录也能跑

from .main import main

if __name__ == '__main__':
    main()