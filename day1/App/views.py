from django.shortcuts import render, redirect, HttpResponse
import re
import time
import requests

# Create your views here.


CURRENT_TIME = None

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

    return render(request, '')