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
        ret['status'] = 200  # 解决我们后台的报错问题，因为前台一直在pending获取数据根后台我们拿到的数据不一致
    return HttpResponse(json.dumps(ret))


