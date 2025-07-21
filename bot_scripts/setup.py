# 标准库
from enum import Enum

# 第三方库
import pyrogram
from pyrogram.types import BotCommand, BotCommandScopeAllPrivateChats

# 自定义模块
from app import get_bot_app
from libs.log import logger


ADMINS: dict[str, pyrogram.types.User] = {}


class CommandScope(Enum):
    PRIVATE_CHATS = BotCommandScopeAllPrivateChats()


BOT_COMMANDS: list[tuple[BotCommand, list[CommandScope]]] = [
    (
        BotCommand("start", "基础设置"),
        [CommandScope.PRIVATE_CHATS],
    ),
    (
        BotCommand("helpme", "查看帮助信息"),
        [CommandScope.PRIVATE_CHATS],
    ),
    (
        BotCommand("update", "更新机器人"),
        [CommandScope.PRIVATE_CHATS],
    ),
    (
        BotCommand("restart", "重启脚本"),
        [CommandScope.PRIVATE_CHATS],
    ),
    (
        BotCommand("dajie", "朱雀dajie相关设置"),
        [CommandScope.PRIVATE_CHATS],
    ),
    (
        BotCommand("blacklist", "朱雀dajie不予返现黑名设置"),
        [CommandScope.PRIVATE_CHATS],
    ),
    (
        BotCommand("ydx", "朱雀ydx菠菜自动投注设置"),
        [CommandScope.PRIVATE_CHATS],
    ),
    (
        BotCommand("autofire", "朱雀自动释放技能开关"),
        [CommandScope.PRIVATE_CHATS],
    ),
    (
        BotCommand("card", "朱雀道具卡回收"),
        [CommandScope.PRIVATE_CHATS],
    ),
    (
        BotCommand("lotterysw", "小菜自动参与抽奖开关"),
        [CommandScope.PRIVATE_CHATS],
    ),
    (
        BotCommand("lotteryuser", "魔力类中奖领奖用PT站点用户名"),
        [CommandScope.PRIVATE_CHATS],
    ),
    (
        BotCommand("lotterytime", "小菜自动参与抽奖时间段"),
        [CommandScope.PRIVATE_CHATS],
    ),
    (
        BotCommand("autochangename", "自动修改报时昵称"),
        [CommandScope.PRIVATE_CHATS],
    ),
    (
        BotCommand("leaderboard", "转入排名图片开关"),
        [CommandScope.PRIVATE_CHATS],
    ),
    (
        BotCommand("payleaderboard", "转出排名图片开关"),
        [CommandScope.PRIVATE_CHATS],
    ),
    (
        BotCommand("notification", "转入转出消息提示开关"),
        [CommandScope.PRIVATE_CHATS],
    ),
    (
        BotCommand("ssd_click", "SSD大额转账自动确认设置"),
        [CommandScope.PRIVATE_CHATS],
    ),
    (
        BotCommand("cookie", "设定网页的cookie"),
        [CommandScope.PRIVATE_CHATS],
    ),
    (
        BotCommand("xcsrf", "设定网页的x-csrf"),
        [CommandScope.PRIVATE_CHATS],
    ),
    (
        BotCommand("set115tocms", "share115tocms所需的配置设定如embyapi"),
        [CommandScope.PRIVATE_CHATS],
    ),
    (
        BotCommand("blockyword", "share115tocms不检索关键字设定"),
        [CommandScope.PRIVATE_CHATS],
    ),
    (
        BotCommand("share115tocms", "share115tocms 启用开关"),
        [CommandScope.PRIVATE_CHATS],
    ),
    (
        BotCommand("configstate", "查看当前参数状态"),
        [CommandScope.PRIVATE_CHATS],
    ),
    (
        BotCommand("sysstate", "查看当前登录状态"),
        [CommandScope.PRIVATE_CHATS],
    ),
    (
        BotCommand("export", "数据库导出文件"),
        [CommandScope.PRIVATE_CHATS],
    ),
    (
        BotCommand("scheduler_jobs", "查询定时任务"),
        [CommandScope.PRIVATE_CHATS],
    ),
]


async def setup_commands():
    bot_app = get_bot_app()
    scopes_dict: dict[str, list[BotCommand]] = {
        scope.name: [] for scope in CommandScope
    }
    # 清除旧命令
    await bot_app.delete_bot_commands()

    # 添加新命令
    for cmd, scopes in BOT_COMMANDS:
        for scope in scopes:
            scopes_dict[scope.name].append(cmd)
    logger.info("正在设置命令...")
    for scope, commands in scopes_dict.items():
        try:
            logger.info(f"设置命令: {scope}, {commands}")
            await bot_app.set_bot_commands(commands, scope=CommandScope[scope].value)
        except Exception as e:
            logger.error(f"设置命令失败: {e}")
