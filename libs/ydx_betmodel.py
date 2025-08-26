from abc import ABC, abstractmethod
from app import logger
import random
import logging
from pathlib import Path
import asyncio
from datetime import datetime, timedelta
import telegram
from telegram import Update
from telegram.ext import CallbackContext

# 高频日志记录器
hight_logger = logging.getLogger("hight")
hight_logger.setLevel(logging.INFO)
hight_logger.propagate = False

if not hight_logger.handlers:
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True, parents=True)
    handler = logging.FileHandler(log_dir / "hight.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s"))
    hight_logger.addHandler(handler)
    
# ================= Telegram 回调优化函数 =================
def is_query_valid(query) -> bool:
    """检查查询是否过期（超过2分钟）"""
    if not query.message:
        return False
    
    query_time = query.message.date
    current_time = datetime.utcnow()
    return (current_time - query_time) < timedelta(minutes=2)

async def safe_edit_message(context: CallbackContext, chat_id: int, message_id: int, text: str, retry=0):
    """带重试机制的安全消息编辑函数"""
    try:
        await context.bot.edit_message_text(
            text=text,
            chat_id=chat_id,
            message_id=message_id
        )
    except telegram.error.RetryAfter as e:
        # 处理速率限制
        wait_time = e.retry_after + random.uniform(0.5, 2.0)
        logger.warning(f"速率限制，等待 {wait_time:.1f}秒")
        await asyncio.sleep(wait_time)
        return await safe_edit_message(context, chat_id, message_id, text, retry+1)
    except telegram.error.BadRequest as e:
        if "Message is not modified" in str(e):
            # 忽略无害的"消息未修改"错误
            pass
        elif "Query is too old" in str(e):
            logger.warning(f"过期查询: {message_id}")
            raise  # 直接抛出不再重试
        elif retry < 3:
            wait_time = 2 ** retry + random.uniform(0.5, 2.0)
            logger.warning(f"Telegram API 错误，重试#{retry+1}: {e}")
            await asyncio.sleep(wait_time)
            return await safe_edit_message(context, chat_id, message_id, text, retry+1)
        else:
            logger.error(f"消息编辑失败: {e}")
            raise
    except Exception as e:
        if retry < 3:
            wait_time = 2 ** retry + random.uniform(0.5, 2.0)
            logger.warning(f"编辑消息错误，重试#{retry+1}: {e}")
            await asyncio.sleep(wait_time)
            return await safe_edit_message(context, chat_id, message_id, text, retry+1)
        else:
            logger.error(f"消息编辑失败: {e}")
            raise

async def process_callback(query, context: CallbackContext):
    """后台处理回调的耗时操作"""
    try:
        # ========================
        # 这里放置您原有的回调处理逻辑
        # 例如：
        # data = query.data
        # result = await your_main_processing_function(data)
        # result_text = format_result(result)
        # ========================
        
        # 示例：模拟耗时操作
        await asyncio.sleep(5)
        result_text = "✅ 处理完成！"
        
        # 使用安全的消息编辑方法
        await safe_edit_message(
            context=context,
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
            text=result_text
        )
    except telegram.error.BadRequest as e:
        if "Query is too old" in str(e):
            logger.warning(f"过期查询: {query.data}")
        else:
            logger.error(f"Telegram API 错误: {e}")
    except Exception as e:
        logger.exception(f"后台处理错误: {e}")
        # 尝试向用户发送错误通知
        try:
            await context.bot.answer_callback_query(
                callback_query_id=query.id,
                text="处理请求时出错，请重试",
                show_alert=True
            )
        except Exception:
            pass

async def callback_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    
    try:
        # 1. 检查查询有效性
        if not is_query_valid(query):
            await query.answer(text="❌ 操作已过期，请重新开始", show_alert=True)
            return
        
        # 2. 立即响应 Telegram（关键步骤！）
        await query.answer()
        
        # 3. 启动后台处理
        asyncio.create_task(process_callback(query, context))
        
    except Exception as e:
        logger.exception("回调处理异常")
        try:
            await query.answer(text="⚠️ 系统错误，请稍后再试", show_alert=True)
        except Exception:
            pass
# ================= Telegram 回调优化函数结束 =================

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
        
        # 获取位置值
        last_1 = data[-1]
        last_40 = data[-40]
        
        # 高频 & 高频=最新值=参考点
        if self.high_count is not None and self.high_count == last_1 and self.high_count == last_40:
            self.guess_dx = self.high_count

        # 高频 & 最新值=参考点
        elif self.high_count is not None and last_1 == last_40:
            self.guess_dx = last_1
        
        # 无高频 & 最新值=参考点
        elif self.high_count is None and last_1 == last_40:
            self.guess_dx = 1 - last_1
        
        # 无高频 & 最新值≠参考点
        elif self.high_count is None and last_1 != last_40:
            self.guess_dx = last_1
        
        # 默认模式：反投
        else:
            self.guess_dx = 1 - last_1

        # 预测日志记录
        hight_logger.info(
            f"高频统计 | 样本数:{len(analysis_data)} "
            f"0出现:{count_0}次 1出现:{count_1}次 "
            f"高频结果:{self.high_count} "
            f"最新值:{last_1} "
            f"参考值:{last_40 if last_40 is not None else 'N/A'} "
            f"预测结果:{self.guess_dx}"
        )
            
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
