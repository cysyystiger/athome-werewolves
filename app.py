from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *


#======這裡是呼叫的檔案內容=====
#======這裡是呼叫的檔案內容=====

#======python的函數庫==========
import tempfile, os
import datetime
import time
from collections import Counter
from queue import Queue
from random import shuffle
#======python的函數庫==========

app = Flask(__name__)
static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')
# Channel Access Token
line_bot_api = LineBotApi('BhzsxLLDA32COtlegQFFfQcZCTrVywgY5qPvFf03K2eP0McC4P0I/Gx2fMsKr9w0z8zzZwONeo4VG2xWV1xjYvs32pU2uvNriu+gHjxnV5TAEnKzN7HPjlDwcgYMefnAB7n4WbpmvCZ1D643+uPfHQdB04t89/1O/w1cDnyilFU=')
# Channel Secret
handler = WebhookHandler('a6ab3a9d53fd2e33b9b7a53f890fb36e')

class Data():
    def __init__(self):
        self.reset()
        self.specialSkill = {
            '預言家':'查驗',
            '女巫':'用藥',
            '守衛':'盾牌',
            '獵人':'獵槍',
            '狼弟':'復仇',
            }


    def reset(self):
        self.state = 'none'
        self.player = set()
        self.seat = set()
        self.role = []
        self.startRole = []
        self.order = ['狼弟', '狼兄', '狼王', '狼人', '預言家', '女巫', '守衛', '獵人']

        #狼刀
        self.killed = []

        #女巫
        self.save = False
        self.drug = '-1'

        #守衛
        self.protected = '0'

        #狼弟
        self.revenge = False

        self.isDone = Counter()

        # 出局
        self.out = set()

    def isEndTxt(self):
        txt = ''
        wolf_num = 0
        god_num = 0
        man_num = 0
        for seat in self.seat:
            role = self.startRole[self.seat.index(seat)]
            if  role in ['狼人', '狼王', '狼兄', '狼弟']:
                wolf_num += 1
            elif role in ['平民']:
                man_num += 1
            else:
                god_num += 1
        for seat in self.out:
            role = self.startRole[self.seat.index(seat)]
            if  role in ['狼人', '狼王', '狼兄', '狼弟']:
                wolf_num -= 1
            elif role in ['平民']:
                man_num -= 1
            else:
                god_num -= 1
        if god_num == 0 or man_num == 0:
            txt += '\n遊戲結束，狼人獲勝'
        elif wolf_num == 0:
            txt += '\n遊戲結束，好人獲勝'
        return txt

    def nextRound(self):
        self.killed = []

        self.isDone = Counter()

        self.justRevenge = False


data = Data()

def Verify(func):
    def wrapper(**kwargs):
        user_id = kwargs['user_id']
        data = kwargs['data']
        if user_id not in data.player:
            return TextSendMessage(text='不是玩家')
        else:
            return func(**kwargs)
    return wrapper

def VerifyRight(right=None):
    def decorator(func):
        @Verify
        def wrapper(**kwargs):
            user_id = kwargs['user_id']
            data = kwargs['data']
            role = data.role[data.player.index(user_id)]
            if role not in right:
                return TextSendMessage(text='你的角色不能執行此動作')
            else:
                return func(**kwargs)
        return wrapper
    return decorator

def IsState(states=None):
    def decorator(func):
        def wrapper(**kwargs):
            data = kwargs['data']
            if data.state not in states:
                return TextSendMessage(text='現在不能做此動作')
            else:
                return func(**kwargs)
        return wrapper
    return decorator

def Done(no=None):
    def decorator(func):
        def wrapper(**kwargs):
            if data.isDone[no] == 1:
                return TextSendMessage(text='已經做過此動作')
            data.isDone[no] += 1
            return func(**kwargs)
        return wrapper
    return decorator

@IsState(states = ['none'])
def CreateGame(data=None):
    data.state = 'created'
    buttons = ButtonsTemplate(
                    title = "成功建立房間",
                    text = "大家請私訊機器人：加 or +",
                    actions = [
                        PostbackTemplateAction(
                            label = '人數',
                            data = '人數'
                        ),
                        PostbackTemplateAction(
                            label = '開始',
                            data = '開始'
                        )
                    ]
                )
    return TemplateSendMessage(alt_text="成功建立房間", template=buttons)

@IsState(states = ['created'])
def PlayOne(user_id=None, data=None):
    if user_id in data.player:
        return TextSendMessage(text='已經是玩家')
    elif len(data.player) == 12:
        return TextSendMessage(text='玩家數已滿')
    else:
        data.player.add(user_id)

        seat = str(len(data.player))
        if len(seat) == 1:
            seat = '0'+seat
        data.seat.add(seat)

        buttons = ButtonsTemplate(
                    title = "成功加入遊戲",
                    text = "等待群組開始遊戲後\n點擊'身分'",
                    actions = [
                        PostbackTemplateAction(
                            label = '身分',
                            data = '身分'
                        )
                    ]
                )
        return TemplateSendMessage(alt_text="成功加入遊戲", template=buttons)

@IsState(states = ['created'])
def SetRole(msg=None, data=None):
    data.role = msg.split()[1:]
    data.startRole = msg.split()[1:]
    return TextSendMessage(text="成功配置：現在有 "+str(len(data.role))+" 個角色")

@IsState(states = ['day'])
def GoDie(msg=None, data=None):
    die = msg.split()[1]
    if data.role[data.seat.index(die)] == '狼兄':
        data.revenge = True
    data.out.add(die)
    return TextSendMessage(text="成功放逐玩家："+die+data.isEndTxt())

@IsState(states = ['day'])
@Done(no='死訊')
def ShowDead(data=None):
    die = []
    if data.save == True and data.protected == data.killed[0]:
        die.append(data.killed[0])
    elif data.save != True:
        for i in range(len(data.killed)):
            die.append(data.killed[i])
        if len(data.killed) > 0 and data.protected in data.killed:
            die.remove(data.protected)
    if data.save == True:
        data.save = None
    if data.drug in data.seat:
        die.append(data.drug)
        data.drug = '100'
    die = sorted(die)
    for seat in die:
        data.out.add(seat)
        if data.role[data.seat.index(seat)] == '狼兄':
            data.revenge = True
    txt = ''
    if len(die) == 0:
        txt += '無人'
    return TextSendMessage(text='昨晚 '+txt+' '.join(die)+' 死亡'+data.isEndTxt())

@IsState(states = ['created'])
def PlayNum(data=None):
    return TextSendMessage(text='目前 '+str(len(data.player))+' 人在房間')

@IsState(states = ['created'])
def StartGame(data=None):
    if len(data.player) > 0 and len(data.player) != len(data.role):
        return TextSendMessage(text='人數與角色數不符')
    else:
        data.state = 'day'

        data.seat = sorted(data.seat)
        shuffle(data.seat)

        data.player = sorted(data.player)
        shuffle(data.player)

        buttons = ButtonsTemplate(
                    title = "遊戲開始",
                    text = "請私訊點擊'身分'",
                    actions = [
                        PostbackTemplateAction(
                            label = '天黑請閉眼',
                            data = '下一輪'
                        )
                    ]
                )
        return TemplateSendMessage(alt_text="遊戲開始", template=buttons)

#  以下開始要改
@IsState(states = ['day'])
def NextRound(data=None):
    data.state = 'night'
    data.nextRound()
    buttons = ButtonsTemplate(
                title = '天黑請閉眼',
                text = "所有玩家回房後主持人請點擊'確認'",
                actions = [
                    PostbackTemplateAction(
                        label = '確認',
                        data = '第一位'
                    )
                ]
            )

    return TemplateSendMessage(alt_text='天黑請閉眼', template=buttons)

@Verify
@IsState(states = ['day','night'])
def CheckRole(user_id=None, data=None):
    idx = data.player.index(user_id)
    role = data.startRole[idx]
    seat = data.seat[idx]
    txt = '你是：'+role+'/座位：'+seat
    buttons = ButtonsTemplate(
                    title = txt,
                    text = "換你的時候請點'換我'",
                    actions = [
                        PostbackTemplateAction(
                            label = '換我',
                            data = '換我'
                        )
                    ]
                )
    return TemplateSendMessage(alt_text=txt, template=buttons)

@Verify
@IsState(states = ['night'])
def NextOne(msg=None, user_id=None, data=None):
    idx = data.player.index(user_id)
    role = data.startRole[idx] #夜間流程要用 startRole
    seat = data.seat[idx]
    def brotherMessage(now: str):
        if now != '沒人':
            buttons = ButtonsTemplate(
                    title = '輪到狼兄狼弟，由狼弟操作',
                    text = "僅第一晚見面\n之後狼弟自己行動\n-----\n私訊'換我'\n->操作完\n->回大群'確認'",
                    actions = [
                        PostbackTemplateAction(
                            label = '確認',
                            data = '下一位'
                        )
                    ]
                )
            return TemplateSendMessage(alt_text=now+'輪到狼兄狼弟', template=buttons)
        else:
            data.state = 'day'
            buttons = ButtonsTemplate(
                    title = '天亮囉',
                    text = "所有玩家請至大廳討論",
                    actions = [
                        PostbackTemplateAction(
                            label = '死訊',
                            data = '死訊'
                        ),
                        PostbackTemplateAction(
                            label = '下一次天黑（回房後再按）',
                            data = '下一輪'
                        )
                    ]
                )
            return TemplateSendMessage(alt_text=now+'天亮囉', template=buttons)

    def killerMessage(now: str):
        if now != '沒人':
            buttons = ButtonsTemplate(
                title = '狼人現身請至大廳',
                text = "選擇要擊殺的玩家\n->點擊'確認'\n->各自回房",
                actions = [
                    PostbackTemplateAction(
                        label = '確認',
                        data = '下一位'
                    )
                ]
            )

            item = []
            item.append(QuickReplyButton(action=PostbackAction(label='不做事', data='不做事')))
            for s in sorted(data.seat):
                if s not in data.out:
                    item.append(QuickReplyButton(action=PostbackAction(label=s, data=s)))

            quickReply = QuickReply(
                items = item
            )

            return TemplateSendMessage(alt_text='狼人現身請至大廳', template=buttons, quick_reply=quickReply)
        else:
            data.state = 'day'
            buttons = ButtonsTemplate(
                    title = '天亮囉',
                    text = "所有玩家請至大廳討論",
                    actions = [
                        PostbackTemplateAction(
                            label = '死訊',
                            data = '死訊'
                        ),
                        PostbackTemplateAction(
                            label = '下一次天黑（回房後再按）',
                            data = '下一輪'
                        )
                    ]
                )
            return TemplateSendMessage(alt_text=now+'天亮囉', template=buttons)

    def Message(now: str):
        if now != '沒人':
            buttons = ButtonsTemplate(
                    title = now+'換你囉',
                    text = "私訊'換我'\n->操作完\n->回大群'確認'",
                    actions = [
                        PostbackTemplateAction(
                            label = '確認',
                            data = '下一位'
                        )
                    ]
                )
            return TemplateSendMessage(alt_text=now+'換你囉', template=buttons)
        else:
            data.state = 'day'
            buttons = ButtonsTemplate(
                    title = '天亮囉',
                    text = "所有玩家請至大廳討論",
                    actions = [
                        PostbackTemplateAction(
                            label = '死訊',
                            data = '死訊'
                        ),
                        PostbackTemplateAction(
                            label = '天黑請閉眼',
                            data = '下一輪'
                        )
                    ]
                )
            return TemplateSendMessage(alt_text='天亮囉', template=buttons)

    if msg == '第一位':
        for now in ['狼弟', '狼兄', '狼王', '狼人', '預言家', '女巫', '守衛', '獵人']:
            if now in data.startRole:
                if now == '狼弟':
                    return brotherMessage(now)
                elif now in ['狼兄', '狼王', '狼人']:
                    return killerMessage('狼人')
                else:
                    return Message(now)
    elif role in ['狼弟', '狼兄']:
        for now in ['狼人', '狼兄', '狼王']:
            if now in data.startRole:
                return killerMessage('狼人')
        for now in ['預言家', '女巫', '守衛', '獵人']:
            if now in data.startRole:
                return Message(now)
    elif role in ['狼人', '狼王', '狼兄']:
        for now in ['預言家', '女巫', '守衛', '獵人']:
            if now in data.startRole:
                return Message(now)
    elif role in ['預言家']:
        for now in ['女巫', '守衛', '獵人']:
            if now in data.startRole:
                return Message(now)
    elif role in ['女巫']:
        for now in ['守衛', '獵人']:
            if now in data.startRole:
                return Message(now)
    elif role in ['守衛']:
        for now in ['獵人']:
            if now in data.startRole:
                return Message(now)
    elif role in ['獵人']:
        for now in []:
            if now in data.startRole:
                return Message(now)
    return Message('沒人')

@VerifyRight(right = ['狼弟', '預言家', '女巫', '守衛', '獵人'])
@IsState(states = ['night'])
def MyTurn(user_id=None, data=None):
    idx = data.player.index(user_id)
    role = data.role[idx]
    @Done(no=data.specialSkill[role])
    def Func(user_id=None, data=None):
        idx = data.player.index(user_id)
        role = data.role[idx]
        seat = data.seat[idx]
        if role == '狼弟':
            txt = ''
            item = []
            if data.revenge == False:
                txt += '狼兄還沒死還不能復仇'
                item.append(QuickReplyButton(action=PostbackAction(label='確認', data='無法')))
            elif data.revenge == None:
                txt += '記得之後要跟狼人一起睜眼'
                item.append(QuickReplyButton(action=PostbackAction(label='確認', data='無法')))
            else:
                txt += '請選擇要使用復仇刀的對象'
                for s in sorted(data.seat):
                    if s not in data.out:
                        item.append(
                            QuickReplyButton(action=PostbackAction(label=s, data=s))
                        )
                data.revenge = None
                data.justRevenge = True
                data.role[data.role.index('狼弟')] = '狼人'

            quickReply = QuickReply(
                items = item
            )
            return TextSendMessage(text=txt, quick_reply=quickReply)
        if role == '預言家':
            item = []
            for s in sorted(data.seat):
                if s not in data.out:
                    item.append(
                        QuickReplyButton(action=PostbackAction(label=s, data=s))
                    )
            quickReply = QuickReply(
                items = item
            )
            return TextSendMessage(text="請選擇要查驗的對象", quick_reply=quickReply)
        if role == '女巫':
            txt = "？"
            item = []
            item.append(QuickReplyButton(action=PostbackAction(label='不做事', data='不做事')))
            if data.save == False:
                if len(data.killed) > 0 and not (len(data.killed) == 1 and data.justRevenge == True):
                    txt = data.killed[0]
                else:
                    txt = '沒人'
                if txt != '沒人':
                    item.append(QuickReplyButton(action=PostbackAction(label='救', data='救')))
            if data.drug == '-1':
                for s in sorted(data.seat):
                    if s != seat and s not in data.out:
                        item.append(
                            QuickReplyButton(action=PostbackAction(label=s, data=s))
                        )
            quickReply = QuickReply(
                items = item
            )
            return TextSendMessage(text=txt+" 被殺，救或毒？", quick_reply=quickReply)
        if role == '守衛':
            item = []
            item.append(QuickReplyButton(action=PostbackAction(label='不做事', data='不做事')))
            for s in sorted(data.seat):
                if s not in  data.out and s != data.protected:
                    item.append(
                        QuickReplyButton(action=PostbackAction(label=s, data=s))
                    )
            quickReply = QuickReply(
                items = item
            )
            return TextSendMessage(text="請選擇要守護的對象", quick_reply=quickReply)
        if role == '獵人':
            gun = '可開槍'
            item = []
            item.append(QuickReplyButton(action=PostbackAction(label='不做事', data='不做事')))
            quickReply = QuickReply(
                items = item
            )
            if data.drug == int(seat):
                gun = '不可開槍'
            return TextSendMessage(text="開槍手勢："+gun, quick_reply=quickReply)
    return Func(user_id=user_id, data=data)

@VerifyRight(right = ['狼人', '狼王', '狼兄', '狼弟', '預言家', '女巫', '守衛', '獵人'])
@IsState(states = ['night'])
def Mention(msg=None, user_id=None, data=None):
    mention_role = ''
    if msg in data.seat:
        mention_role = data.role[data.seat.index(msg)]
    role = data.role[data.player.index(user_id)]
    if role in ['狼人', '狼王', '狼兄', '狼弟']:
        if msg != '不做事':
            data.killed.append(msg)
            if len(data.killed) == 2:
                tmp = data.killed[0]
                data.killed[0] = data.killed[1]
                data.killed[1] = tmp
        if role == '狼弟' and msg == '無法':
            buttons = ButtonsTemplate(
                    title = '收到',
                    text = "你做完動作了，下個夜晚再行動",
                    actions = [
                        PostbackTemplateAction(
                            label = '換我',
                            data = '換我'
                        )
                    ]
                )
            return TemplateSendMessage(alt_text='收到', template=buttons)
        else:
            return TextSendMessage(text='收到，請按確認。')
    elif role == '預言家':
        team = '好人'
        if mention_role in ['狼人', '狼王', '狼兄']:
            team = '狼人'
        txt = msg+' 號玩家屬於：'+team
        buttons = ButtonsTemplate(
                    title = txt,
                    text = "你做完動作了，下個夜晚再行動",
                    actions = [
                        PostbackTemplateAction(
                            label = '換我',
                            data = '換我'
                        )
                    ]
                )
        return TemplateSendMessage(alt_text=txt, template=buttons)
    elif role in ['女巫', '守衛', '獵人']:
        if role == '女巫':
            if msg == '救':
                data.save = True
            elif msg in data.seat:
                data.drug = msg
        elif role == '守衛':
            if msg in data.seat:
                data.protected = msg
            elif msg == '不做事':
                data.protected = '0'
        buttons = ButtonsTemplate(
                    title = '收到',
                    text = "你做完動作了，下個夜晚再行動",
                    actions = [
                        PostbackTemplateAction(
                            label = '換我',
                            data = '換我'
                        )
                    ]
                )
        return TemplateSendMessage(alt_text='收到', template=buttons)

# 以下不用改
@IsState(states = ['night'])
def StopGame(data=None):
    data.state = 'stop'
    return TextSendMessage(text='暫停遊戲')

@IsState(states = ['stop'])
def ResumeGame(data=None):
    data.state = 'night'
    return TextSendMessage(text='遊戲繼續')

@IsState(states = ['created', 'stop', 'day', 'night'])
def CloseGame(data=None):
    data.reset()
    return TextSendMessage(text='房間關閉')

# 監聽所有來自 /callback 的 Post Request
@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# 處理回傳
@handler.add(PostbackEvent)
def handle_postback(event):
    msg = event.postback.data
    user_id = event.source.user_id

    if msg == '人數':
        message = PlayNum(data=data)
        line_bot_api.reply_message(event.reply_token, message)

    if msg == '開始':
        message = StartGame(data=data)
        line_bot_api.reply_message(event.reply_token, message)

    if msg == '身分':
        message = CheckRole(user_id=user_id, data=data)
        line_bot_api.reply_message(event.reply_token, message)

    if msg == '換我':
        message = MyTurn(user_id=user_id, data=data)
        line_bot_api.reply_message(event.reply_token, message)

    if msg == '下一輪':
        message = NextRound(data=data)
        line_bot_api.reply_message(event.reply_token, message)

    if msg in ['第一位', '下一位']:
        message = NextOne(msg=msg, user_id=user_id, data=data)
        line_bot_api.reply_message(event.reply_token, message)

    if msg == '死訊':
        message = ShowDead(data=data)
        line_bot_api.reply_message(event.reply_token, message)

    if msg in data.seat or msg in ['不做事', '救', '無法']:
        message = Mention(msg=msg, user_id=user_id, data=data)
        line_bot_api.reply_message(event.reply_token, message)

# 處理訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text
    user_id = event.source.user_id
    if msg == '開房':
        message = CreateGame(data=data)
        line_bot_api.reply_message(event.reply_token, message)

    if msg in ['++', '+', '+1', '加加', '加']:
        message = PlayOne(user_id=user_id, data=data)
        line_bot_api.reply_message(event.reply_token, message)

    if '配置' in msg:
        message = SetRole(msg=msg, data=data)
        line_bot_api.reply_message(event.reply_token, message)

    if '放逐' in msg:
        message = GoDie(msg=msg, data=data)
        line_bot_api.reply_message(event.reply_token, message)

    if msg == '暫停':
        message = StopGame(data=data)
        line_bot_api.reply_message(event.reply_token, message)

    if msg == '繼續':
        message = ResumeGame(data=data)
        line_bot_api.reply_message(event.reply_token, message)

    if msg == '關閉':
        message = CloseGame(data=data)
        line_bot_api.reply_message(event.reply_token, message)

import os
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
