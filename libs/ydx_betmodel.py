from abc import ABC, abstractmethod
from app import logger
import random
import logging
from pathlib import Path

# 高频日志记录器
hight_logger = logging.getLogger("hight")
hight_logger.setLevel(logging.INFO)
hight_logger.propagate = False

# 策略A日志记录器
hight_class_logger = logging.getLogger("hight_class")
hight_class_logger.setLevel(logging.INFO)
hight_class_logger.propagate = False

log_dir = Path("logs")
log_dir.mkdir(exist_ok=True, parents=True)

# 配置日志处理器
if not hight_logger.handlers:
    # 高频日志
    hight_handler = logging.FileHandler(log_dir / "hight.log", encoding="utf-8")
    hight_handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s"))
    hight_logger.addHandler(hight_handler)
    
    # 策略A日志
    class_hight_handler = logging.FileHandler(log_dir / "hight_class.log", encoding="utf-8")
    class CustomFormatter(logging.Formatter):
        def format(self, record):
            parts = record.msg.split("|")
            if len(parts) == 4:
                high_value, last_1, last_40, prediction = parts
            else:
                high_value = last_1 = last_40 = prediction = "N/A"
                
            now = datetime.now()
            date_str = now.strftime("%Y年%m月%d日").replace("年0", "年").replace("月0", "月")  # 移除补零
            time_str = now.strftime("%H:%M:%S")
            
            return (
                f"日期：{date_str}，"
                f"时间：{time_str}，"
                f"高频计算结果={high_value}，"
                f"最新值={last_1}，"
                f"参考值={last_40}，"
                f"预测结果={prediction}"
            )
    
    class_hight_handler.setFormatter(CustomFormatter())
    hight_class_logger.addHandler(class_hight_handler)

class BetModel(ABC):
    fail_count: int = 0
    guess_dx: int = -1

    @abstractmethod
    def guess(self, data):
        pass

    def test(self, data: list[int]):
        loss_count = [0 for _ in range(50)]
        turn_loss_count = 0
        win_count = 0
        total_count = 0
        for i in range(41, len(data) + 1):
            data_i = data[i - 41 : i]
            dx = self.guess(data_i)
            if i < len(data):
                total_count += 1
                self.set_result(data[i])
                if data[i] == dx:
                    loss_count[turn_loss_count] += 1
                    win_count += 1
                    turn_loss_count = 0
                else:
                    turn_loss_count += 1
        max_nonzero_index = next(
            (
                index
                for index, value in reversed(list(enumerate(loss_count)))
                if value != 0
            ),
            -1,
        )
        return {
            "loss_count": loss_count[: max_nonzero_index + 1],
            "max_nonzero_index": max_nonzero_index,
            "win_rate": win_count / total_count,
            "win_count": 2 * win_count - total_count,
            "turn_loss_count": turn_loss_count,
            "guess": dx,
        }

    def set_result(self, result: int):
        """更新连败次数,在监听结果中调用了"""
        if self.guess_dx != -1:
            if result == self.guess_dx:
                self.fail_count = 0
            else:
                self.fail_count += 1

    def get_consecutive_count(self, data: list[int]):
        """
        根据秋人结果计算连大连小次数
        """
        if not data:
            return 0
        last = data[-1]
        count = 0
        for v in reversed(data):
            if v == last:
                count += 1
            else:
                break
        dx = "小大"
        logger.info(f"连{dx[last]} [{count}]次")
        return count

    def get_bet_count(self, data: list[int], start_count=0, stop_count=0):
        """根据配置计算当前下注多少次"""
        consecutive_count = self.get_consecutive_count(data)
        bet_count = consecutive_count - start_count
        if 0 <= bet_count < stop_count:
            return bet_count
        return -1
        
    def get_bet_bonus(self, start_bonus, bet_count):
        """计算下注金额（基于连败次数）"""
        return start_bonus * (2 ** (bet_count + 1) - 1)

class A(BetModel):
    """正向的智能预测策略"""
    def guess(self, data):
        # 高频统计逻辑
        analysis_data = data[-41:] if len(data) >= 41 else data
        count_0 = analysis_data.count(0)
        count_1 = analysis_data.count(1)
        if count_0 > count_1:
            self.high_count = 0
        elif count_1 > count_0:
            self.high_count = 1
        else:
            self.high_count = None

        # 高频日志记录
        #hight_logger.info(
            #f"高频统计 | 样本数:{len(analysis_data)} "
            #f"0出现:{count_0}次 1出现:{count_1}次 "
            #f"高频结果:{self.high_count}"
        #)

        # 主级模式
        if self.fail_count == 5:
            if self.high_count is not None:
                if self.high_count == data[-1]:
                    self.guess_dx = data[-1]  # 高频正投
                else:
                    self.guess_dx = 1 - data[-1]  # 不高频反投
            else:
                self.guess_dx = 1 - data[-1]  # 高频结果为None时反投
            return self.guess_dx
        
        # 默认模式：正投
        self.guess_dx = data[-1]
        return self.guess_dx

    def get_bet_count(self, data: list[int], start_count=0, stop_count=0):
        bet_count = self.fail_count - start_count
        if 0 <= bet_count < stop_count:
            return bet_count
        return -1

class B(BetModel):
    """反转的智能预测策略"""
    def guess(self, data):
        """计算高频结果"""
        analysis_data = data[-41:] if len(data) >= 41 else data
        
        count_0 = analysis_data.count(0)
        count_1 = analysis_data.count(1)
        
        if count_0 > count_1:
            self.high_count = 0
        elif count_1 > count_0:
            self.high_count = 1
        else:
            self.high_count = None

        # 主级模式：反转策略
        if len(data) >= 5:
            last_5 = data[-5:]
            if all(x == 0 for x in last_5) and self.high_count is not None:
                if self.high_count == data[-1]:
                    self.guess_dx = data[-1]  # 高频正投
                else:
                    self.guess_dx = 1 - data[-1]  # 不高频反投
                return self.guess_dx
        
        # 默认模式：固定预测
        self.guess_dx = 1 - data[-1]
        return self.guess_dx

    def get_bet_count(self, data: list[int], start_count=0, stop_count=0):
        bet_count = self.fail_count - start_count
        if 0 <= bet_count < stop_count:
            return bet_count
        return -1
        
class E(BetModel):
    """智能预测策略"""
    def guess(self, data):
        # 高频统计
        analysis_data = data[-41:] if len(data) >= 41 else data
        count_0 = analysis_data.count(0)
        count_1 = analysis_data.count(1)
        if count_0 > count_1:
            self.high_count = 0
        elif count_1 > count_0:
            self.high_count = 1
        else:
            self.high_count = None

        # 高频日志记录
        hight_logger.info(
            f"高频统计 | 样本数:{len(analysis_data)} "
            f"0出现:{count_0}次 1出现:{count_1}次 "
            f"高频结果:{self.high_count}"
        )

        # 长度检查
        if len(data) < 40:
            # 数据不足时使用默认正投策略
            self.guess_dx = data[-1] if data else 0
            # 记录日志（数据不足）
            self.log_prediction("N/A", data[-1] if data else "N/A", "N/A", self.guess_dx)
            return self.guess_dx
        
        # 获取位置值
        last_1 = data[-1]
        last_40 = data[-40]
        
        # 高频 与 高频=最新值=参考点
        if self.high_count is not None and self.high_count == last_1 and self.high_count == last_40:
            self.guess_dx = last_1
        
        # 高频 & 最新值≠参考点
        elif self.high_count is not None and last_1 != last_40:
            self.guess_dx = self.high_count
        
        # 无高频 & 最新值=参考点
        elif self.high_count is None and last_1 == last_40:
            self.guess_dx = last_1
        
        # 无高频 & 最新值≠参考点
        elif self.high_count is None and last_1 != last_40:
            self.guess_dx = last_40
        
        # 默认模式：正投
        else:
            self.guess_dx = last_1
        
        self.log_prediction(self.high_count, last_1, last_40, self.guess_dx)
        
        return self.guess_dx

    def log_prediction(self, high_value, last_1, last_40, prediction):
        """记录策略A专用日志"""
        high_str = str(high_value) if high_value is not None else "None"
        last_1_str = str(last_1)
        last_40_str = str(last_40)
        prediction_str = str(prediction)
        log_message = f"{high_str}|{last_1_str}|{last_40_str}|{prediction_str}"
        hight_class_logger.info(log_message)

    def get_bet_count(self, data: list[int], start_count=0, stop_count=0):
        bet_count = self.fail_count - start_count
        if 0 <= bet_count < stop_count:
            return bet_count
        return -1

models: dict[str, BetModel] = {"a": A(), "b": B(), "e": E()}

def test(data: list[int]):
    data.reverse()
    ret = {}
    for model in models:
        ret[model] = models[model].test(data)
    return ret
