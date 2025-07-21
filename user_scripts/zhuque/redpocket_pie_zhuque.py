# 标准库
import re
from decimal import Decimal

# 第三方库
from pyrogram import filters, Client
from pyrogram.types import Message

# 自定义模块
from app import get_bot_app
from config.config import PT_GROUP_ID, MY_TGID
from filters import custom_filters
from libs.log import logger
from models.redpocket_db_modle import Redpocket



TARGET = [-1001833464786, -1002262543959]
SITE_NAME = "zhuque"
BONUS_NAME = "灵石"
redpockets = {}


async def in_redpockets_filter(_, __, m: Message):
    return bool(m.text in redpockets)


@Client.on_message(
    filters.chat(TARGET)
    & custom_filters.zhuque_bot
    & filters.regex(
        r"内容: ([\s\S]*?)\n灵石: (\d+(?:\.\d+)?)/\d+(?:\.\d+)?\n剩余: .*?\n大善人: (.*)"
    )
)
async def get_redpocket_gen(client: Client, message: Message):
    bot_app = get_bot_app()
    if message.reply_to_message.from_user.id == MY_TGID:
        try:
            await Redpocket.add_redpocket_record(
                SITE_NAME,
                "redpocker",
                Decimal(f"-{message.matches[0].group(2)}"),
            )
        except Exception as e:
            logger.exception(f"提交失败: 用户消息, 错误：{e}")

    callback_data = message.reply_markup.inline_keyboard[0][0].callback_data
    match = message.matches[0]
    redpocket_name = match.group(1)
    red_from_user = match.group(3)
    retry_times = 0
    MAX_RETRY = 500
    RETRY_DELAY = 0.2  # 秒

    for retry_times in range(MAX_RETRY):
        try:
            result_message = await client.request_callback_answer(
                chat_id=message.chat.id,
                message_id=message.id,
                callback_data=callback_data,
                timeout=5        
            )
            
                    
        except TimeoutError:
            logger.warning("CallbackAnswer 超时，可能是 Telegram 卡顿或 query 已失效")
            
        except Exception as e:
            logger.exception(f"第 {retry_times + 1} 次提交失败: 请求回调异常: {e}")
            return  # 退出重试（你可以选择改为 `continue` 来忽略单次失败）
        
        # 匹配抢红包成功的消息
        match = re.search(r"已获得 (\d+) 灵石", result_message.message)
        if match:
            bonus = match.group(1)

            # 通知 BOT 群组
            await bot_app.send_message(
                PT_GROUP_ID["BOT_MESSAGE_CHAT"],
                f"```\n{red_from_user}发的:\n朱雀红包 {redpocket_name}:\n抢了 {retry_times + 1} 次，成功抢到 {bonus} 灵石",
            )
            try:
                await Redpocket.add_redpocket_record(SITE_NAME, "redpocket", bonus)
            except Exception as e:
                logger.exception(f"提交失败: 用户消息, 错误：{e}")
            return
        retry_times += 1


@Client.on_message(
    filters.chat(TARGET)
    & filters.regex(r"天上掉馅饼啦, \+(\d+\.\d+)")
    & custom_filters.zhuque_bot
    & custom_filters.reply_to_me
)
async def zhuque_pie(client: Client, message: Message):
    bonus = message.matches[0].group(1)
    try:
        await Redpocket.add_redpocket_record(SITE_NAME, "pie", bonus)
    except Exception as e:
        logger.exception(f"提交失败: 用户消息, 错误：{e}")
