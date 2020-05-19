# -*- coding: UTF-8 -*-
from nonebot import on_command, CommandSession,NoticeSession,on_notice,permission as perm
from helper import commandHeadtail,keepalive,getlogger,msgSendToBot,CQsessionToStr
from module.twitter import push_list,decode_b64,encode_b64
import time
import asyncio
import os
import traceback
import config
logger = getlogger(__name__)
__plugin_name__ = '通用推特监听指令'
__plugin_usage__ = r"""
用于配置推特监听
详见：
https://github.com/chenxuan353/tweetToQQbot
"""

#推特事件处理对象，由启动调用的更新检测方法有关
#allow_start_method = ('twitter_api','socket_api','twint')
if config.UPDATA_METHOD == 'twitter_api':
    import module.twitterApi as tweetListener
else:
    raise Exception('暂不支持的更新检测(UPDATA_METHOD)方法：'+config.UPDATA_METHOD)
tweet_event_deal = tweetListener.tweet_event_deal

@on_command('delall',aliases=['这里单推bot'], permission=perm.SUPERUSER | perm.PRIVATE_FRIEND | perm.GROUP_OWNER,only_to_me = True)
async def delalltest(session: CommandSession):
    await asyncio.sleep(0.2)
    message_type = session.event['message_type']
    sent_id = 0
    if message_type == 'private':
        sent_id = session.event['user_id']
    elif message_type == 'group':
        sent_id = session.event['group_id']
    else:
        await session.send('未收录的消息类型:'+message_type)
        return
    sent_id = str(sent_id)
    res = push_list.delPushunitFromPushTo(message_type,int(sent_id),self_id=int(session.event['self_id']))
    push_list.savePushList()
    logger.info(CQsessionToStr(session))
    await session.send('已移除此地所有监测' if res[0] == True else res[1])

#获取指定推送对象的推送列表（推送标识，推送对象ID）
def get_pushTo_spylist(message_type:str,pushTo:int,page:int):
    if message_type not in push_list.message_type_list:
        raise Exception("无效的消息类型！",message_type)
    table = push_list.getLitsFromPushToAndID(message_type,pushTo)
    s = ''
    unit_cout = 0
    for key in table:
        if ((unit_cout//5)+1) == page:
            s = s + (table[key]['nick'] if table[key]['nick'] != '' else tweet_event_deal.tryGetNick(key,"未定义昵称")) + \
                "," + str(key) + ',' + table[key]['des'] + "\n"
        unit_cout = unit_cout + 1
    totalpage = (unit_cout-1)//5 + (0 if unit_cout%5 == 0 else 1)
    if unit_cout > 5 or page != 1:
        s = s + '页数：' + str(page) + '/' + str(totalpage) + ' '
    s = s + '总监测数：' + str(unit_cout)
    if unit_cout == 0:
        s = s + '\n' + '单 推 b o t'
    return s
@on_command('getpushlist',aliases=['DD列表'],permission=perm.SUPERUSER | perm.PRIVATE_FRIEND | perm.GROUP_ADMIN | perm.GROUP_OWNER,only_to_me = False)
async def getpushlist(session: CommandSession):
    await asyncio.sleep(0.1)
    page = 1
    stripped_arg = session.current_arg_text.strip().lower()
    if stripped_arg != '':
        if not stripped_arg.isdecimal():
            await session.send("参数似乎有点不对劲？请再次检查o(￣▽￣)o")
            return
        page = int(stripped_arg)
        if page < 1:
            await session.send("参数似乎有点不对劲？请再次检查o(￣▽￣)o")
            return
    message_type = session.event['message_type']
    sent_id = 0
    if message_type == 'private':
        sent_id = session.event['user_id']
    elif message_type == 'group':
        sent_id = session.event['group_id']
    else:
        await session.send('未收录的消息类型:'+message_type)
        return
    s = get_pushTo_spylist(message_type,sent_id,page)
    await session.send(s)
    logger.info(CQsessionToStr(session))

#获取推送对象总属性设置
def getPushToSetting(message_type:str,pushTo:int) -> str:
    attrlist = {    
        'upimg':'图片',#是否连带图片显示(默认不带)-发推有效,转推及评论等事件则无效
        #推特推送模版
        'retweet_template':'转推模版',
        'quoted_template':'转推并评论模版',
        'reply_to_status_template':'回复模版',
        'reply_to_user_template':'提及模版', 
        'none_template':'发推模版',
        
        #推特推送开关
        'retweet':'转推',#转推(默认不开启)
        'quoted':'转推并评论',#带评论转推(默认开启)
        'reply_to_status':'回复',#回复(默认开启)
        'reply_to_user':'提及',#提及某人-多数时候是被提及但是被提及不会接收(默认开启)
        'none':'发推',#发推(默认开启)

        #个人信息变化推送(非实时)
        'change_ID':'ID修改', #ID修改(默认关闭)
        'change_name':'昵称修改', #昵称修改(默认开启)
        'change_description':'描述修改', #描述修改(默认关闭)
        'change_headimgchange':'头像修改', #头像更改(默认开启)
    }
    res = ''
    attrs = push_list.getAttrLitsFromPushTo(message_type,pushTo)
    if attrs == {}:
        return 'BOT酱还没有初始化哦 请至少添加一个检测对象来开始使用我吧~'
    for key,value in attrs.items():
        res = res + attrlist[key] + ':'  + \
            (value if value not in (0,1,'') else {0:'关闭',1:'开启','':'未定义'}[value]) + '\n'
    return res
@on_command('getGroupSetting',aliases=['全局设置列表'],permission=perm.SUPERUSER | perm.PRIVATE_FRIEND | perm.GROUP_ADMIN | perm.GROUP_OWNER,only_to_me = True)
async def setGroupSetting(session: CommandSession):
    await asyncio.sleep(0.2)
    logger.info(CQsessionToStr(session))
    res = getPushToSetting(
        session.event['message_type'],
        session.event[('group_id' if session.event['message_type'] == 'group' else 'user_id')]
    )
    await session.send(res)
#获取某个单元的推送设置列表
def userinfoToStr(userinfo):
    if userinfo:
        res = "\n" + '用户名：' + userinfo['name'] + "\n" +\
            '用户昵称：' + userinfo['screen_name'] + "\n"
        return res
    return ''
def getPushUnitSetting(message_type:str,pushTo:int,tweet_user_id:int) -> str:
    attrlist = {    
        'upimg':'图片',#是否连带图片显示(默认不带)-发推有效,转推及评论等事件则无效
        #推特推送模版
        'retweet_template':'转推模版',
        'quoted_template':'转推并评论模版',
        'reply_to_status_template':'回复模版',
        'reply_to_user_template':'提及模版', 
        'none_template':'发推模版',
        
        #推特推送开关
        'retweet':'转推',#转推(默认不开启)
        'quoted':'转推并评论',#带评论转推(默认开启)
        'reply_to_status':'回复',#回复(默认开启)
        'reply_to_user':'提及',#提及某人-多数时候是被提及但是被提及不会接收(默认开启)
        'none':'发推',#发推(默认开启)

        #个人信息变化推送(非实时)
        'change_ID':'ID修改', #ID修改(默认关闭)
        'change_name':'昵称修改', #昵称修改(默认开启)
        'change_description':'描述修改', #描述修改(默认关闭)
        'change_headimgchange':'头像修改', #头像更改(默认开启)
    }
    res = push_list.getPushunit(message_type,pushTo,tweet_user_id)
    if res[0]:
        Pushunit = res[1]
    else:
        return res
    """
        #固有属性
        Pushunit['bindCQID'] = bindCQID #绑定的酷Q帐号(正式上线时将使用此帐户进行发送，用于适配多酷Q账号)
        Pushunit['type'] = pushtype #group/private
        Pushunit['pushTo'] = pushID #QQ号或者群号
        Pushunit['tweet_user_id'] = tweet_user_id #监测ID
        Pushunit['nick'] = nick #推送昵称(默认推送昵称为推特screen_name)
        Pushunit['des'] = des #单元描述
        userinfo['id'] = user.id
        userinfo['id_str'] = user.id_str
        userinfo['name'] = user.name
        userinfo['description'] = user.description
        userinfo['screen_name'] = user.screen_name
        userinfo['profile_image_url'] = user.profile_image_url
        userinfo['profile_image_url_https'] = user.profile_image_url_https
    """
    if tweetListener:
        userinfo = tweet_event_deal.tryGetUserInfo(tweet_user_id)
    res = '用户ID:' + str(tweet_user_id) + "\n" + \
        '自定义的昵称:' + (Pushunit['nick'] if Pushunit['nick'] != '' else '未定义') + "\n" +\
        '描述:' + Pushunit['des'].replace("\\n","\n") + \
        userinfoToStr(userinfo)
    for attrname,attrdisplayname in attrlist.items():
        value = push_list.getPuslunitAttr(Pushunit,attrname)
        res = res + '\n' + attrdisplayname + ':' + \
            (value[1] if value[1] not in (0,1,'') else {0:'关闭',1:'开启','':'未定义'}[value[1]])
    return (True,res)
@on_command('getSetting',aliases=['对象设置列表'],permission=perm.SUPERUSER | perm.PRIVATE_FRIEND | perm.GROUP_ADMIN | perm.GROUP_OWNER,only_to_me = True)
async def getSetting(session: CommandSession):
    await asyncio.sleep(0.2)
    stripped_arg = session.current_arg_text.strip().lower()
    if stripped_arg == '':
        await session.send("还没有添加参数哦~")
        return
    #处理用户ID
    tweet_user_id : int = -1
    if stripped_arg.isdecimal():
        tweet_user_id = int(stripped_arg)
    else:
        await session.send("用户ID似乎有点问题，请再次检查ヽ(；´Д｀)ﾉ")
        return
    res = getPushUnitSetting(
        session.event['message_type'],
        session.event[('group_id' if session.event['message_type'] == 'group' else 'user_id')],
        tweet_user_id
    )
    logger.info(CQsessionToStr(session))
    await session.send(res[1])

#推送对象总属性设置
@on_command('setGroupAttr',aliases=['全局设置'],permission=perm.SUPERUSER | perm.PRIVATE_FRIEND | perm.GROUP_ADMIN | perm.GROUP_OWNER,only_to_me = True)
async def setGroupAttr(session: CommandSession):
    await asyncio.sleep(0.2)
    stripped_arg = session.current_arg_text.strip().lower()
    if stripped_arg == '':
        await session.send("还没有添加参数哦~")
        return
    Pushunit_allowEdit = {
        #携带图片发送
        'upimg':'upimg','图片':'upimg','img':'upimg',
        #昵称设置
        #'nick':'nick','昵称':'nick',
        #消息模版
        'retweet_template':'retweet_template','转推模版':'retweet_template',
        'quoted_template':'quoted_template','转推并评论模版':'quoted_template',
        'reply_to_status_template':'reply_to_status_template','回复模版':'reply_to_status_template',
        'reply_to_user_template':'reply_to_user_template','被提及模版':'reply_to_user_template',
        'none_template':'none_template','发推模版':'none_template',
        #推特转发各类型开关
        'retweet':'retweet','转推':'retweet',
        'quoted':'quoted','转推并评论':'quoted',
        'reply_to_status':'reply_to_status','回复':'reply_to_status',
        'reply_to_user':'reply_to_user','被提及':'reply_to_user_template',
        'none':'none','发推':'none',
        #推特个人信息变动推送开关
        'change_id':'change_ID','ID改变':'change_ID','ID修改':'change_ID',
        'change_name':'change_name','名称改变':'change_name','名称修改':'change_name','名字改变':'change_name','名字修改':'change_name','昵称修改':'change_name',
        'change_description':'change_description','描述改变':'change_description','描述修改':'change_description',
        'change_headimgchange':'change_headimgchange','头像改变':'change_headimgchange','头像修改':'change_headimgchange'
        }
    template_attr = (
        'retweet_template',
        'quoted_template',
        'reply_to_status_template',
        'reply_to_user_template',
        'none_template'
    )
    cs = commandHeadtail(stripped_arg)
    cs = {
        0:cs[0],
        1:cs[1],
        2:cs[2].strip()
    }
    if cs[0] == '' or cs[2] == '':
        await session.send("还没有添加参数哦~")
        return
    if cs[0] not in Pushunit_allowEdit:
        await session.send('属性值不存在！')
        return
    PushTo : int = 0
    if session.event['message_type'] == 'group':
        PushTo = int(session.event['group_id'])
    elif session.event['message_type'] == 'private':
        PushTo = int(session.event['user_id'])
    else:
        await session.send('不支持的消息类型!')
        return
    if cs[2] != '' and Pushunit_allowEdit[cs[0]] in template_attr:
        cs[2] = cs[2].replace("\\n","\n")
        res = push_list.PushTo_setAttr(
            session.event['message_type'],
            PushTo,
            Pushunit_allowEdit[cs[0]],
            cs[2]
        )
    elif cs[2] in ('true','开','打开','开启','1'):
        res = push_list.PushTo_setAttr(
            session.event['message_type'],
            PushTo,
            Pushunit_allowEdit[cs[0]],
            1
        )
    elif cs[2] in ('false','关','关闭','0'):
        res = push_list.PushTo_setAttr(
            session.event['message_type'],
            PushTo,
            Pushunit_allowEdit[cs[0]],
            0
        )
    else:
        res = (False,'属性的值不合法！')
        await session.send(res[1])
        return
    push_list.savePushList()
    logger.info(CQsessionToStr(session))
    await session.send(res[1])
#推送对象的监测对象属性设置
@on_command('setAttr',aliases=['对象设置'],permission=perm.SUPERUSER | perm.PRIVATE_FRIEND | perm.GROUP_ADMIN | perm.GROUP_OWNER,only_to_me = True)
async def setAttr(session: CommandSession):
    await asyncio.sleep(0.2)
    stripped_arg = session.current_arg_text.strip().lower()
    if stripped_arg == '':
        await session.send("还没有添加参数哦~")
        return
    cs = commandHeadtail(stripped_arg)
    cs = {
        0:cs[0],
        1:cs[1],
        2:cs[2].strip()
    }
    if cs[0] == '' or cs[2] == '':
        await session.send("还没有添加参数哦~")
        return
    #处理用户ID
    tweet_user_id : int = -1
    if cs[0].isdecimal():
        tweet_user_id = int(cs[0])
    else:
        await session.send("用户ID错误")
        return
    if cs[2].strip() == '':
        await session.send("还没有添加参数哦~")
        return
    tcs = commandHeadtail(cs[2])
    cs[2] = tcs[0]
    cs[3] = tcs[1]
    cs[4] = tcs[2].strip()
    PushTo : int = 0
    if session.event['message_type'] == 'group':
        PushTo = int(session.event['group_id'])
    elif session.event['message_type'] == 'private':
        PushTo = int(session.event['user_id'])
    else:
        await session.send('不支持的消息类型!')
        return
    Pushunit_allowEdit = {
        #携带图片发送
        'upimg':'upimg','图片':'upimg','img':'upimg',
        #昵称设置
        'nick':'nick','昵称':'nick',
        #描述设置
        'des':'des','描述':'des',
        #消息模版
        'retweet_template':'retweet_template','转推模版':'retweet_template',
        'quoted_template':'quoted_template','转推并评论模版':'quoted_template',
        'reply_to_status_template':'reply_to_status_template','回复模版':'reply_to_status_template',
        'reply_to_user_template':'reply_to_user_template','被提及模版':'reply_to_user_template',
        'none_template':'none_template','发推模版':'none_template',
        #推特转发各类型开关
        'retweet':'retweet','转推':'retweet',
        'quoted':'quoted','转推并评论':'quoted',
        'reply_to_status':'reply_to_status','回复':'reply_to_status',
        'reply_to_user':'reply_to_user','被提及':'reply_to_user_template',
        'none':'none','发推':'none',
        #推特个人信息变动推送开关
        'change_id':'change_ID','ID改变':'change_ID',
        'change_name':'change_name','名称改变':'change_name',
        'change_description':'change_description','描述改变':'change_description',
        'change_headimgchange':'change_headimgchange','头像改变':'change_headimgchange'
        }
    template_attr = (
        'retweet_template',
        'quoted_template',
        'reply_to_status_template',
        'reply_to_user_template',
        'none_template'
    )
    if str(tweet_user_id) not in push_list.spylist:
        await session.send("用户不在监测列表内！")
        return
    if cs[2] not in Pushunit_allowEdit:
        await session.send('属性值不存在！')
        return
    if Pushunit_allowEdit[cs[2]] == 'des' or Pushunit_allowEdit[cs[2]] == 'nick':
        res = push_list.setPushunitAttr(
            session.event['message_type'],
            PushTo,
            tweet_user_id,
            Pushunit_allowEdit[cs[2]],
            cs[4]
        )
    elif cs[4] != '' and Pushunit_allowEdit[cs[2]] in template_attr:
        res = push_list.setPushunitAttr(
            session.event['message_type'],
            PushTo,
            tweet_user_id,
            Pushunit_allowEdit[cs[2]],
            cs[4]
        )
    elif cs[4] in ('true','开','打开','开启','1'):
        res = push_list.setPushunitAttr(
            session.event['message_type'],
            PushTo,
            tweet_user_id,
            Pushunit_allowEdit[cs[2]],
            1
        )
    elif cs[4] in ('false','关','关闭','0'):
        res = push_list.setPushunitAttr(
            session.event['message_type'],
            PushTo,
            tweet_user_id,
            Pushunit_allowEdit[cs[2]],
            0
        )
    else:
        res = (False,'属性的值不合法！')
        await session.send(res[1])
        return
    push_list.savePushList()
    await session.send(res[1])
    logger.info(CQsessionToStr(session))

#移除某个人或某个群的所有监测，用于修复配置错误(退出群/删除好友时不在线)
@on_command('globalRemove',aliases=['全局移除'],permission=perm.SUPERUSER,only_to_me = True)
async def globalRemove(session: CommandSession):
    await asyncio.sleep(0.2)
    stripped_arg = session.current_arg_text.strip().lower()
    if stripped_arg == '':
        await session.send("似乎少了点什么!?试着添加QQ号或群号作为参数吧~")
        return
    cs = commandHeadtail(stripped_arg)
    cs = {
        'messagetype':cs[0],
        'pushto':cs[2].strip()
    }
    if cs['pushto'] == '' or cs['messagetype'] == '':
        await session.send("似乎少了点什么!?请检查参数是否正确(／_＼)")
        return
    if not cs['pushto'].isdecimal():
        await session.send("QQ号或群号似乎怪怪的？请再次检查:"+cs['pushto'])
        return
    messagetype_list = {
        '私聊':'private',
        'private':'private',
        '群聊':'group',
        'group':'group',
        '好友':'private',
        '群':'group',
    }
    if cs['messagetype'] in messagetype_list:
        res = push_list.delPushunitFromPushTo(
            messagetype_list[cs['messagetype']],
            int(cs['pushto']),
            self_id=int(session.event['self_id'])
        )
        push_list.savePushList()
        logger.info(CQsessionToStr(session))
        await session.send(res[1])
    else:
        await session.send("此消息类型不支持:"+cs['messagetype'])
        return

#推特ID编码解码
@on_command('detweetid',aliases=['推特ID解压','解压ID'],only_to_me = False)
async def decodetweetid(session: CommandSession):
    await asyncio.sleep(0.2)
    stripped_arg = session.current_arg_text.strip()
    if stripped_arg == '':
        return
    res = decode_b64(stripped_arg)
    if res == -1:
        await session.send("唔orz似乎没有这个推特ID的缩写呢")
        return
    logger.info(CQsessionToStr(session))
    await session.send("推特ID的真身已判明(ﾟ▽ﾟ)/其名为："+str(res))

@on_command('entweetid',aliases=['推特ID压缩','压缩ID'],only_to_me = False)
async def encodetweetid(session: CommandSession):
    await asyncio.sleep(0.2)
    stripped_arg = session.current_arg_text.strip()
    if stripped_arg == '':
        return
    if not stripped_arg.isdecimal():
        await session.send("推特ID似乎搞错了呢(￣▽￣)\"请仔细检查")
        return
    res = encode_b64(int(stripped_arg))
    logger.info(CQsessionToStr(session))
    await session.send("推特ID压缩好了(oﾟ▽ﾟ)o请使用："+res)

@on_command('about',aliases=['帮助','help','关于'],only_to_me = False)
async def about(session: CommandSession):
    logger.info(CQsessionToStr(session))
    msg = 'http://uee.me/dfRwA'
    await session.send("想了解我的全部，就来{}这里看看吧~".format(msg))
"""
	'font': , 
    'message': [{'type': 'text', 'data': {'text': '!getpushlist'}}], 
    'message_id': , 
    'message_type': 'private', 
    'post_type': 'message', 
    'raw_message': '!getpushlist', 
    'self_id': , 
    'sender': {'age': , 'nickname': '', 'sex': '', 'user_id': }, 
    'sub_type': 'friend', 
    'time': , 
    'user_id': , 
    'to_me': True}
"""