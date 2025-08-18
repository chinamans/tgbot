from abc import ABC, abstractmethod
from app import logger
import random

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
        for i in range(40, len(data) + 1):
            data_i = data[i - 40 : i]
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

        # 主级模式
        if len(data) >= 5:
            last_5 = data[-5:]
            if last_5 == [0, 1, 0, 1, 0] or last_5 == [1, 0, 1, 0, 1]:
                if self.high_count is not None:
                    # 高频=0 → 预测0；高频=1 → 预测1
                    self.guess_dx = 0 if self.high_count == 0 else 1
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
    """固定1的智能预测策略"""
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
                if self.high_count == 0:
                    self.guess_dx = 0  # 高频=0 → 预测0
                else:
                    self.guess_dx = 1  # 高频≠0 → 预测1
                return self.guess_dx
        
        # 默认模式：固定预测
        self.guess_dx = 1
        return self.guess_dx

    def get_bet_count(self, data: list[int], start_count=0, stop_count=0):
        bet_count = self.fail_count - start_count
        if 0 <= bet_count < stop_count:
            return bet_count
        return -1
        
class E(BetModel):
    """固定预测1，下注周期内满足条件时重置状态"""
    def guess(self, data):
        # 固定预测1
        self.guess_dx = 1
        return self.guess_dx

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
