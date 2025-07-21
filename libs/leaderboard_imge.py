# 标准库
import os
import uuid
from pathlib import Path

# 第三方库
import imgkit

# 自定义模块
from config import config


medal_emojis = {
    1: "🥇",
    2: "🥈",
    3: "🥉"
}

medal_emoji_others = "🪙"

async def get_leaderboard(data,direction):
    # 配置 wkhtmltoimage 路径
    if os.name == "nt":
        wkhtmltoimage_path = r"D:\Tool Software\wkhtmltopdf\bin\wkhtmltoimage.exe"
        wkhtml_config = imgkit.config(wkhtmltoimage=wkhtmltoimage_path)
    elif os.name == "posix":
        wkhtml_config = None

    rows = ""
    table_title = "打赏" if direction != "pay" else "孝敬"

    
    for rank, uid, username, count, amount in data:
        emoji = medal_emojis.get(rank, medal_emoji_others)
        medal_img = f'{emoji} TOP{rank}'
        rows += f"""
        <tr>
            <td>{medal_img}</td>
            <td>{mask_tgid(uid)}</td>
            <td>{username}</td>
            <td>{count}</td>
            <td>{amount}</td>
        </tr>
        """

    html_str = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            table {{
                border-collapse: collapse;
                width: 100%;
                font-family: 'Microsoft YaHei', sans-serif;
                font-size: 14px;
            }}
            th, td {{
                border: 1px solid #999;
                padding: 6px;
                text-align: center;
            }}
            thead {{
                background-color: #4a72b2;
                color: white;
            }}
            caption {{
                caption-side: top;
                font-size: 16px;
                font-weight: bold;
                background-color: #4a72b2;
                color: white;
                padding: 6px;
                border: 1px solid #999;
            }}
        </style>
    </head>
    <body>
        <table>
            <caption>🌟🏅🎉 {config.MY_NAME}的个人{table_title}榜 🎉🏅🌟</caption>
            <thead>
                <tr>
                    <th>排名</th>
                    <th>TGID</th>
                    <th>用户名</th>
                    <th>打赏次数</th>
                    <th>打赏金额</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
    </body>
    </html>
    """
    unique_id = uuid.uuid4().hex
    html_file = Path(f"temp_file/temp_{unique_id}.html")
    img_file = Path(f"temp_file/leaderboard_{unique_id}.png")
    html_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_str)

    options = {
        'encoding': "UTF-8",
        'format': 'png',
        'width': 512,
        'enable-local-file-access': '',
        'quiet': ''
    }

    imgkit.from_file(str(html_file), str(img_file), options=options, config=wkhtml_config)

    Path(html_file).unlink()    
    return img_file
    


def mask_tgid(tgid):
    tgid_str = str(tgid)
    if len(tgid_str) <= 4:
        return tgid_str  # 长度不足 5，直接返回原样
    return tgid_str[:2] + '*' * (len(tgid_str) - 4) + tgid_str[-2:]