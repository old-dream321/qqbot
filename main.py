"""
    基于qq频道机器人的一个聊天机器人
    前置库:
        qq-botpy, revChatGPT, easy_ernie, bardapi
"""
import json
import os
import traceback
import requests

import botpy
from bardapi import Bard, SESSION_HEADERS
from botpy.message import *
from easy_ernie import Ernie
from revChatGPT.V1 import Chatbot


# 创建数据文件
if not os.path.isfile("./data.json"):
    with open("./data.json", "a+") as fp:
        json.dump({
            "version": "0.0.1",
            "public": {},
            "private": {},
        }, fp)
# 创建配置文件
if not os.path.isfile("./config.json"):
    with open("./config.json", "a+") as fp:
        json.dump({
            "version": "0.0.1",
            "qqbot": {
                "appid": "",
                "token": ""
            },
            "ChatGPT": {
                "access_token": ""
            },
            "Ernie": {
                "BAIDUUID": "",
                "BDUSS_BFESS": ""
            },
            "Bard": {
                "__Secure-1PSID": "",
                "__Secure-1PSIDCC": "",
                "__Secure-1PSIDTS": ""
            },
            "allowed_channels": [],
            "proxies": {}
        }, fp)
    print("配置文件已创建，请先填写")
    exit(0)

with open("./data.json", "r") as f:
    dt = json.load(f)
with open("./config.json", "r") as fa:
    cfg = json.load(fa)
# 需提前写好子频道白名单
allowed_channels = cfg.get("allowed_channels")


# 保存数据文件
def save():
    with open("./data.json", "w") as fp:
        json.dump(dt, fp)


# 模型列表
models = ["chatGPT", "文心一言", "Bard"]

# 模型初始化
ernie = Ernie(BAIDUID=cfg["Ernie"].get("BAIDUUID"),
              BDUSS_BFESS=cfg["Ernie"].get("BDUSS_BFESS"))

chatbot = Chatbot(config={"access_token": cfg["ChatGPT"].get("access_token")})

bard_session = requests.Session()
bard_token = cfg["Bard"].get("__Secure-1PSID")
bard_session.cookies.set("__Secure-1PSID", bard_token)
bard_session.cookies.set("__Secure-1PSIDCC", cfg["Bard"].get("__Secure-1PSIDCC"))
bard_session.cookies.set("__Secure-1PSIDTS", cfg["Bard"].get("__Secure-1PSIDTS"))
bard_session.headers = SESSION_HEADERS
bard = Bard(
    token=bard_token,
    session=bard_session,
    proxies=cfg.get("proxies")
)


# 初始化子频道
def channel_init(guild_id, channel_id):
    global dt
    channel = dt["public"][guild_id][channel_id]
    try:
        if not channel.get("chatGPT"):
            # GPT
            channel["chatGPT"] = {}
            chatbot.reset_chat()
            resp = ''
            for data in chatbot.ask(
                    "你好"
            ):
                resp = data
            channel["chatGPT"]["cv_id"] = resp.get('conversation_id')

        if not channel.get("ernie"):
            # yiyan
            channel["ernie"] = {}
            sid = ernie.newConversation(guild_id + ":" + channel_id)
            cid = '0'
            channel['ernie']['sid'] = sid
            channel['ernie']['cid'] = cid
        if not channel.get("Bard"):
            # Bard
            channel["Bard"] = {}
            cid = bard.get_answer("你好").get("conversation_id")
            channel["Bard"]["cid"] = cid

    except:
        print(traceback.format_exc())
    save()


def ask_gpt(message: str, info: list):
    try:
        cv_id = dt[info[0]][info[1]][info[2]]["chatGPT"]["cv_id"]
        resp = ''
        for data in chatbot.ask(
                prompt=message,
                conversation_id=cv_id
        ):
            resp = data
        print(resp)
        return resp["message"]
    except:
        print(traceback.format_exc())
        return "发生错误"


def ask_ernie(message: str, info: list):
    try:
        sid = dt[info[0]][info[1]][info[2]]['ernie']['sid']
        cid = dt[info[0]][info[1]][info[2]]['ernie']['cid']
        resp = ernie.ask(message, sid, cid)
        dt[info[0]][info[1]][info[2]]['ernie']['cid'] = resp['botChatId']
        save()
        print(resp)
        return resp["answer"], resp["urls"]
    except:
        print(traceback.format_exc())
        return "发生错误"


def ask_bard(message: Message, message_text: str, info: list):
    try:
        global bard
        cid = dt[info[0]][info[1]][info[2]]['Bard']['cid']
        bard.conversation_id = cid
        if message.attachments:
            img = message.attachments[0]
            if img.content_type not in ["image/jpeg", "image/png", "image/webp"]:
                return "请发送图片(仅支持jpeg,png,webp格式)"
            img_content = requests.get(
                url="http://" + img.url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36 Edg/117.0.2045.47"
                },
                timeout=10
            ).content
            resp = bard.get_answer(message_text, image=img_content, image_name=img.filename)
        else:
            resp = bard.get_answer(message_text)
        print(resp)
        dt[info[0]][info[1]][info[2]]['Bard']['cid'] = resp["conversation_id"]
        return resp["content"]
    except:
        print(traceback.format_exc())
        return "发生错误"


# 消息处理
class MyClient(botpy.Client):
    async def on_at_message_create(self, message: Message):
        if message.attachments:
            print(message.attachments)
        dt_public = dt.get("public")
        guild_id = message.guild_id
        channel_id = message.channel_id
        msg_id = message.id
        usr_id = message.author.id
        if channel_id in allowed_channels:
            if not dt_public.get(guild_id):
                dt_public[guild_id] = {}
                save()
            if not dt_public[guild_id].get(channel_id):
                dt_public[guild_id][channel_id] = {}
                dt_public[guild_id][channel_id]["type"] = 0
                save()
            channel_init(guild_id, channel_id)
            model_type = dt_public[guild_id][channel_id]["type"]
            message_text = message.content.replace("<@!15619784985663343279>", "")
            message_text = message_text.replace(" ", "")
            img_url = None
            repl_text = None
            if not message_text:
                repl_text = "请说出问题"
            else:
                if message_text[0] != "/":
                    # 正常问题
                    if model_type == 0:
                        repl_text = ask_gpt(message_text, ["public", guild_id, channel_id])
                    elif model_type == 1:
                        repl = ask_ernie(message_text, ["public", guild_id, channel_id])
                        repl_text = repl[0]
                        if repl[1]:
                            img_url = repl[1][0]
                    elif model_type == 2:
                        repl_text = ask_bard(message, message_text, ["public", guild_id, channel_id])
                else:
                    # 指令
                    cmd_text = message_text.replace("/", "")
                    cmd_args = cmd_text.split()
                    if cmd_args[0] == "切换模型":
                        model_type = (model_type + 1 if model_type < 2 else 0)
                        dt_public[guild_id][channel_id]["type"] = model_type
                        save()
                        repl_text = "本子频道模型已切换为：" + models[model_type]
            repl_len = len(repl_text)
            if repl_len < 800:
                await self.api.post_message(channel_id=channel_id, content=f"<@{usr_id}>" + repl_text, msg_id=msg_id,
                                            image=img_url)
            else:
                # 大于800个字分段发送
                await self.api.post_message(channel_id=channel_id, content=f"<@{usr_id}>" + repl_text[:799:],
                                            msg_id=msg_id, image=img_url)
                repl_text = repl_text[799:]
                repl_len -= 800
                while repl_len >= 800:
                    await self.api.post_message(channel_id=channel_id, content=repl_text[:799:], msg_id=msg_id)
                    repl_text = repl_text[799::]
                    repl_len -= 800
                if repl_len > 0:
                    await self.api.post_message(channel_id=channel_id, content=repl_text, msg_id=msg_id)

    async def on_direct_message_create(self, message: DirectMessage):
        ...


if __name__ == "__main__":
    intents = botpy.Intents(public_guild_messages=True, direct_message=True)
    client = MyClient(intents=intents, is_sandbox=True, log_level=20)
    client.run(appid=cfg["qqbot"].get("appid"), token=cfg["qqbot"].get("token"))
