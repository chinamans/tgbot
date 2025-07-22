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
    """反向策略"""
    def guess(self, data):
        self.guess_dx = 1 - data[-1]
        return self.guess_dx

class B(BetModel):
    """正向策略"""
    def guess(self, data):
        self.guess_dx = data[-1]
        return self.guess_dx

    def get_bet_count(self, data: list[int], start_count=0, stop_count=0):
        bet_count = self.fail_count - start_count
        if 0 <= bet_count < stop_count:
            return bet_count
        return -1
        
class E(BetModel):
        """反向智能预测策略"""
    def guess(self, data):
        # 当连败6次时强制使用反向预测
        #if self.fail_count >= 6:
        #    self.guess_dx = 1 - data[-1]
        #    return self.guess_dx

        # 检查最近6局是否相同（暂时不用）
        #if len(data) >= 6:
        #    last_6 = data[-6:]
        #    if all(x == last_6[0] for x in last_6):
        #        self.guess_dx = 1 - data[-1]
        #        return self.guess_dx
        
        # 获取高频数据
        if len(data) >= 5:
            # 获取数据（41场）
            analysis_data = data[-41:] if len(data) >= 41 else data
            
            # 统计频率
            count_0 = analysis_data.count(0)
            count_1 = analysis_data.count(1)
            
            # 确定结果
            if count_0 > count_1:
                high_count = 0
            elif count_1 > count_0:
                high_count = 1
            else:
                high_count = None  # 频率相等时不使用此策略

        # 主级模式：检查前七场
        if len(data) >= 7:
            last_7 = data[-7:]
            # 模型1: 前三相同且后四相同
            pattern1 = (
                all(x == last_7[0] for x in last_7[:3]) and 
                all(x == last_7[3] for x in last_7[3:])
            )
            
            # 模型2: 前四相同且后三相同
            pattern2 = (
                all(x == last_7[0] for x in last_7[:4]) and 
                all(x == last_7[4] for x in last_7[4:])
            )
            
            if pattern1 or pattern2:
                if high_count is not None:
                    first_three = last_7[0]
                    
                    if first_three == high_count:
                        # 一致：预测延续趋势
                        self.guess_dx = last_7[-1]
                    else:
                        # 不一致：预测反转
                        self.guess_dx = 1 - last_7[-1]
                    return self.guess_dx
        
        # 次级模式：反转策略
        if len(data) >= 5:
            # 检查最近4场是否完全相同
            last_4 = data[-4:]
            if all(x == last_4[0] for x in last_4) and high_count is not None:
                # 比较高频结果和最近4次结果
                if last_4[0] == high_count:
                    # 结果一致：预测延续趋势
                    self.guess_dx = last_4[0]
                else:
                    # 结果不一致：预测反转
                    self.guess_dx = 1 - last_4[0]
                return self.guess_dx
        
        # 默认模式：反向预测
        self.guess_dx = 1 - data[-1]
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
