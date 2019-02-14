from django.shortcuts import render, redirect, HttpResponse
import re
import time
import json
import requests

# Create your views here.


QCODE = None
CURRENT_TIME = None
LOGIN_COOKIE_DICT = {}
TICKET_COOKIE_DICT = {}
TICKET_DICT = {}
TIP = 1  # 解决201后还不停pending的问题...
USER_INIT_DATA = {}
BASE_URL = "http://wx.qq.com"
BASE_SYNC_URL = "https://webpush.weixin.qq.com"

def login(request):
    # https://login.wx.qq.com/jslogin?appid=wx782c26e4c19acffb&redirect_uri=https%3A%2F%2Fwx.qq.com%2Fcgi-bin%2Fmmwebwx-bin%2Fwebwxnewloginpage&fun=new&lang=zh_CN&_=1486951705941
    base_qode_url = 'https://login.wx.qq.com/jslogin?appid=wx782c26e4c19acffb&redirect_uri=https%3A%2F%2Fwx.qq.com%2Fcgi-bin%2Fmmwebwx-bin%2Fwebwxnewloginpage&fun=new&lang=zh_CN&={0}'
    global CURRENT_TIME  # 更改全局变量需要更改添加global
    global QCODE

    CURRENT_TIME = str(time.time())  # 时间戳【返回是float类型，转换为str类型】
    q_code_url = base_qode_url.format(CURRENT_TIME)
    response = requests.get(q_code_url)  # 获取到随记字符串,返回是个response对象
    # code: <Response [200]>
    # type(code):  <class 'requests.models.Response'>
    # code.text ： window.QRLogin.code = 200; window.QRLogin.uuid = "gb8OTUPMpA==";
    print('Response对象： ', response, type(response))
    print('Response内容： ', response.text)
    code = re.findall('uuid = "(.*)"', response.text)[0]  # findall返回一个列表，注意空格
    QCODE = code
    print("随记字符：", QCODE)

    return render(request, 'login.html', {"code": QCODE})




def pooling(request):
    # https://login.wx.qq.com/cgi-bin/mmwebwx-bin/login?loginicon=true&uuid=AY0FL0UZwA==&tip=1&r=1700853510&_=1523012536082
    # 201： 扫码，未确认
    # 200： 扫码，确认
    # 408： 等待中...

    global TIP  # 解决201后还不停pending的问题...
    ret = {'status': 408, 'data': None}
    base_login_url = "https://login.wx.qq.com/cgi-bin/mmwebwx-bin/login?loginicon=true&uuid={0}&tip={1}&r=-1700853510&_={2}"
    login_url = base_login_url.format(QCODE, TIP, CURRENT_TIME)
    response_login = requests.get(login_url)
    print('长轮询URL', login_url)
    print('长轮询状态码以及内容：', response_login.text)

    if 'window.code=201' in response_login.text:
        userAvatar = re.findall("userAvatar = '(.*)';", response_login.text)[0]
        ret['data'] = userAvatar
        ret['status'] = 201
        TIP = 0
    elif 'window.code=200' in response_login.text:
        global BASE_URL
        global BASE_SYNC_URL
        # 用户已经确认后获取Cookie内容
        LOGIN_COOKIE_DICT.update(response_login.cookies.get_dict())
        redirect_url = re.findall('window.redirect_uri="(.*)";', response_login.text)[0]
        if redirect_url.startswith('https://wx2.qq.com'):
            BASE_URL = 'https://wx2.qq.com'
            BASE_SYNC_URL = 'https://webpush.wx2.qq.com'
        else:
            BASE_URL = "http://wx.qq.com"
            BASE_SYNC_URL = "https://webpush.weixin.qq.com"

        # 微信正常的：https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxnewloginpage?ticket=ATsWUC3qlrRteYUWzz_8hBMH@qrticket_0&uuid=QY2NxTcDcw==&lang=zh_CN&scan=1523018755&fun=new&version=v2&lang=zh_CN
        # 我们获取的：https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxnewloginpage?ticket=AYTBkpgzEWsIgHOjaQK1tvSs@qrticket_0&uuid=AfxTcp1JXQ==&lang=zh_CN&scan=1523017763
        print('用户确认后获取的URL：', redirect_url)
        redirect_url += '&fun=new&version=v2&lang=zh_CN'
        print('用户确认后改装的跳转URL：', redirect_url)
        # 用户已经确认后获取票据内容
        response_ticket = requests.get(redirect_url, cookies=LOGIN_COOKIE_DICT)
        TICKET_COOKIE_DICT.update(response_ticket.cookies.get_dict())
        '''
            获取的凭据内容：  
                <error>
                    <ret>0</ret>
                    <message></message>
                    <skey>@crypt_ea9ae4c7_090ef27aeb8539e92003afd7658c8f49</skey>
                    <wxsid>dDQOkKqhrvLnFm1o</wxsid>
                    <wxuin>1289256384</wxuin>
                    <pass_ticket>YWQzZ0sOdkr1Eq%2BExvGbyfBq2mbIwksh%2BipMvTyNVUxBwnfqhXKn4wTBPMhpHh%2B%2F</pass_ticket>
                    <isgrayscale>1</isgrayscale>
                </error>
        '''
        print('获取的凭据内容： ', response_ticket.text)  # 利用这个凭据进行下一次的数据访问

        '''
        格式化输出凭据内容
            ret 0
            message None
            skey @crypt_29bab75e_996fb921b5a09570d7793598f2e213dc
            wxsid g++XySA396Bnwljx
            wxuin 1600696821
            pass_ticket fbBFzsSbFhlD1kpNMJ7f39vrBwGqZTezGU7%2FpDZS1rzAueLDfKw%2FfoWp8sT8MdP6
            isgrayscale 1
        '''

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response_ticket.text, 'html.parser')
        for tag in soup.find():  # 格式化打印XML内容
            TICKET_DICT[tag.name] = tag.string  # 字典内部元素修改不需要global,重新赋值需要global
        ret['status'] = 200      # 解决我们后台的报错问题，因为前台一直在pending获取数据根后台我们拿到的数据不一致
    return HttpResponse(json.dumps(ret))


# 获初始化用户信息
def index(request):
    # 用户初始化URL： https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxinit?r=1687552055&lang=zh_CN&pass_ticket=eSd509Kzdhcw4%252BDOYB7s0iV8ik2D%252FxYdOL5fwTSm9cvAaa7sLxZoz3mE88unS4sT
    #【20180410】base_userInit_url = 'https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxinit?r=1692953835&lang=zh_CN&pass_ticket=%s'
    base_userInit_url = BASE_URL + '/cgi-bin/mmwebwx-bin/webwxinit?r=1692953835&lang=zh_CN&pass_ticket=%s'
    userInit_url = base_userInit_url % TICKET_DICT['pass_ticket']
    form_data = {
        'BaseRequest': {
            "DeviceID": "e891769838090373",
            'Sid': TICKET_DICT['wxsid'],
            'Skey': TICKET_DICT['skey'],
            'Uin': TICKET_DICT['wxuin'],
        },
    }

    all_cookiies_dict = {}
    all_cookiies_dict.update(LOGIN_COOKIE_DICT)
    all_cookiies_dict.update(TICKET_COOKIE_DICT)
    response_list = requests.post(userInit_url, json=form_data, cookies=all_cookiies_dict)
    # response_list.encoding('utf8')     错误的
    response_list.encoding = 'utf-8'  # 正确的
    print('用户基本信息：', response_list.text)

    userInit_data = json.loads(response_list.text)
    print('用户字典：')
    for k, v in userInit_data.items():
        print(k, v)
    USER_INIT_DATA.update(userInit_data)  # 获取的值放入全局变量USER_INIT_DATA里

    '''
    USER_INIT_DATA
    User {  'RemarkName': '', 
            'AppAccountFlag': 0, 
            'WebWxPluginSwitch': 3, 
            'HeadImgUrl': '/cgi-bin/mmwebwx-bin/webwxgeticon?seq=1001009474&
            'Signature': "That's all、", 
            'VerifyFlag': 0, 
            'UserName': '@b5c4f49bd9d6c69177777fc7ffcd30c361',
            'Uin': 1600696821, 
            'RemarkPYQuanPin': '', 
            'Sex': 1,
            'ContactFlag': 0, 
            'PYInitial': '', 
            'NickName': 'HHHHHH', 
            'RemarkPYInitial': '', 
            'SnsFlag': 17, 
            'HideInputBarFlag': 0, 
            'HeadImgFlag': 1, 
            'StarFriend': 0, 
            'PYQuanPin': ''}
    '''
    return render(request, 'index.html', {"data": USER_INIT_DATA})

def contactList(request):
    # 获取用户列表： https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxgetcontact?lang=zh_CN&pass_ticket=iH0mJhfpq1FrP44X18ovjrVFJfYqEszXSXGuuknxYJ4MATxoaFuPys&r=152302957&seq=0&skey=@crypt_29c62c055f8ff7e6d66c2fa05fb7
    # 【20180410】base_contactList_url = "https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxgetcontact?lang=zh_CN&pass_ticket={0}&r={1}&seq=0&skey={2}"
    base_contactList_url = BASE_URL + "/cgi-bin/mmwebwx-bin/webwxgetcontact?lang=zh_CN&pass_ticket={0}&r={1}&seq=0&skey={2}"
    contactList_url = base_contactList_url.format(TICKET_DICT['pass_ticket'], str(time.time()), TICKET_DICT['skey'])
    all_cookiies_dict = {}
    all_cookiies_dict.update(LOGIN_COOKIE_DICT)
    all_cookiies_dict.update(TICKET_COOKIE_DICT)
    response = requests.get(contactList_url, cookies=all_cookiies_dict)
    response.encoding = 'utf-8'
    print('联系人列表：', response.text)
    contact_list = json.loads(response.text)
    contact_list_dict = json.loads(response.text)
    for k, v in contact_list.items():
        print(k, v)
    print("获取用户列表__type(contact_list_dict):", type(contact_list_dict))
    return render(request, 'contactList.html', {"obj": contact_list_dict})

# 发送数据 contactList.html一旦加载完成就不停的获取消息
def sendMsg(request):
    from_user_id = USER_INIT_DATA['User']['UserName']
    to_user_id = request.POST.get('user_id')
    msg = request.POST.get('user_msg')
    # 【20180410】BASE_URL = "https://wx2.qq.com"
    # https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxsendmsg?pass_ticket=WGuxtLFLPXUiXteMkgmTmSeq5BPUJlEdXk92%252FtnYEGnj3fnB8K3%252ByODprlQBNC9u
    send_url = BASE_URL + "/cgi-bin/mmwebwx-bin/webwxsendmsg?lang=zh_CN&pass_ticket=" + TICKET_DICT['pass_ticket']
    form_data = {
        'BaseRequest': {
            'DeviceID': 'e531777446530354',
            'Sid': TICKET_DICT['wxsid'],
            'Skey': TICKET_DICT['skey'],
            'Uin': TICKET_DICT['wxuin']
        },
        'Msg': {
            "ClientMsgId": str(time.time()),
            # "Content": '%(content)s',   # 方案二用
            "Content": msg,
            "FromUserName": from_user_id,
            "LocalID": str(time.time()),
            "ToUserName": to_user_id,
            "Type": 1
        },
        'Scene': 0
    }
    # 方案一
    import json
    form_data_str = json.dumps(form_data, ensure_ascii=False)
    form_data_bytes = bytes(form_data_str, encoding='utf-8')

    '''方案二：
    import json
    # form_data_str是字符串
    form_data_str = json.dumps(form_data)
    # 字符串进行格式化
    form_data_str = form_data_str % {'content': msg}  # content是占位符号
    # 字符串转换成字节
    form_data_bytes = bytes(form_data_str, encoding='utf-8')
    '''

    all_cookie_dict = {}
    all_cookie_dict.update(LOGIN_COOKIE_DICT)
    all_cookie_dict.update(TICKET_COOKIE_DICT)
    # 因为我们data发送的字符串，但是微信用的是JSON格式，所以我们需要自己添加请求头
    # 告诉服务器，我发送的是data数据，且是以JSON格式发送  ==》 等价于发送了JSON格式数据
    # requests.post(url, json={'key':'value"})  => requests.post(url, data={'key':'value"},headers={
    # 'Content-Type': 'application/json'})
    # params是get请求
    # data  是post请求
    response = requests.post(url=send_url, data=form_data_bytes, cookies=all_cookie_dict, headers={
        'Content-Type': 'application/json'})

    print("发送消息返回结果：  ", response.text)
    return HttpResponse('ok')


# 接收数据, contactList.html一旦加载完成就不停的获取消息
# 接收消息共2个请求，一个请求负责接收消息， 一个负责查看判断接收消息的类型
def getMsg(request):
    nid = time.time()
    # 检查接收消息类型的URL
    # https://webpush.wx2.qq.com/cgi-bin/mmwebwx-bin/synccheck?r=1523357524934&skey=%40crypt_29bab75e_c405fdf274568e5d5cb96e945449d5bc&sid=PdtuiorPozsWH4r3&uin=1600696821&deviceid=e262718862528046&synckey=1_683967369%7C2_683969564%7C3_683969533%7C11_683969510%7C201_1523357498%7C1000_1523351282%7C1001_1523351354%7C2001_1523351252%7C2002_1523332191&_=1523355846860
    # base_send_url = "https://webpush.wx2.qq.com/cgi-bin/mmwebwx-bin/synccheck?r=1523357524934&skey={0}&sid={1}&uin={2}&deviceid=e262718862528046&synckey={3}&_={4}"
    #【20180410】send_url = "https://webpush.wx2.qq.com/cgi-bin/mmwebwx-bin/synccheck"
    send_url = BASE_SYNC_URL + "/cgi-bin/mmwebwx-bin/synccheck"

    sync_data_list = []
    '''
        SyncKey {
'List': [{
    'Key': 1,
    'Val': 683967369
}, {
    'Key': 2,
    'Val': 683968526
}, {
    'Key': 3,
    'Val': 683968510
}, {
    'Key': 1000,
    'Val': 1523005082
}],
'Count': 4
}
    '''
    for item in USER_INIT_DATA['SyncKey']['List']:
        tmp = "%s_%s" % (item['Key'], item['Val'])  # 拼synckey请求参数
        sync_data_list.append(tmp)
    # 拼凑格式： synckey: 1_683967369|2_683969564|3_683969533|11_683969510
    sync_data_str = "|".join(sync_data_list)
    sync_dict = {
        "r": nid,
        "skey": TICKET_DICT['skey'],
        "sid": TICKET_DICT['wxsid'],
        "uin": TICKET_DICT['wxuin'],
        "deviceid": "e531777446530354",
        "synckey": sync_data_str
    }
    print("拼凑的synckey格式内容为：", sync_dict)
    all_cookie_dict = {}
    all_cookie_dict.update(LOGIN_COOKIE_DICT)
    all_cookie_dict.update(TICKET_COOKIE_DICT)
    # params是get请求
    # data是post请求
    response_sync = requests.get(send_url, params=sync_dict, cookies=all_cookie_dict)
    print("接收消息[检查的GET请求]：", response_sync.text)
    # 获取消息内容的URL
    # 【20180410】fetch_base_url = "https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxsync?sid={0}&skey={1}&pass_ticket={2}"
    fetch_base_url = BASE_URL + "/cgi-bin/mmwebwx-bin/webwxsync?sid={0}&skey={1}&pass_ticket={2}"
    if 'selector:"2"' in response_sync.text:  # 表示请求成功，开始第二次的请求
        fetch_url = fetch_base_url.format(TICKET_DICT['wxsid'], TICKET_DICT['skey'], TICKET_DICT['pass_ticket'])
        form_data = {
            'BaseRequest': {
                'DeviceID': 'e531777446530354',
                'Sid': TICKET_DICT['wxsid'],
                'Skey': TICKET_DICT['skey'],
                'Uin': TICKET_DICT['wxuin']
            },
            'SyncKey': USER_INIT_DATA['SyncKey'],
            'rr': str(time.time())
        }
        fetch_msg_response = requests.post(url=fetch_url, json=form_data, cookies = all_cookie_dict)
        fetch_msg_response.encoding = "utf-8"
        print("POST请求后接收到的微信消息", fetch_msg_response.content)  # content表示一行一行显示内容
        res_fetch_msg_dict = json.loads(fetch_msg_response.text)
        USER_INIT_DATA['SyncKey'] = res_fetch_msg_dict['SyncKey']
        for item in res_fetch_msg_dict['AddMsgList']:
            print('内容为：【', item['Content'], ":::::", '】','来源为',item['FromUserName'], "---->", item['ToUserName'])
    return HttpResponse("OK")
