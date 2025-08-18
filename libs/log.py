# 标准库
import io
import sys
import logging
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler

# 第三方库
import pytz

# 东八区时间格式
class CSTFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        time_utc8 = datetime.fromtimestamp(
            record.created, pytz.timezone("Asia/Shanghai")
        )
        return time_utc8.strftime(datefmt or "%Y-%m-%d %H:%M:%S(%Z)")

# 高频结果专用格式器
class HighFreqFormatter(logging.Formatter):
    """高频结果专用格式器"""
    def formatTime(self, record, datefmt=None):
        time_utc8 = datetime.fromtimestamp(
            record.created, pytz.timezone("Asia/Shanghai")
        )
        return time_utc8.strftime("%Y/%-m/%-d %H:%M")

# 创建 logs 目录
log_path = Path("logs")
log_path.mkdir(parents=True, exist_ok=True)

# 配置主日志记录器
formatter = CSTFormatter("[%(levelname)s] %(asctime)s - %(filename)s - %(message)s")
logger = logging.getLogger("main")
logger.setLevel(logging.INFO)

# 配置高频结果专用记录器
high_freq_logger = logging.getLogger("high_frequency")
high_freq_logger.setLevel(logging.INFO)
high_freq_formatter = HighFreqFormatter("%(asctime)s 高频结果：%(message)s")

# 防止重复添加 handler
if not logger.handlers:
    # 主日志文件处理器（10MB轮转，保留10个备份）
    file_handler = RotatingFileHandler(
        log_path / "Mytgbot.log", 
        maxBytes=10 * 1024 * 1024, 
        backupCount=10, 
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # 主控制台处理器（UTF-8编码）
    utf8_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    console_handler = logging.StreamHandler(utf8_stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

if not high_freq_logger.handlers:
    # 高频结果专用处理器
    high_freq_handler = RotatingFileHandler(
        log_path / "high_freq.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=7,
        encoding="utf-8"
    )
    high_freq_handler.setFormatter(high_freq_formatter)
    high_freq_logger.addHandler(high_freq_handler)
    high_freq_logger.propagate = False
