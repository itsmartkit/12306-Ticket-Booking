# -*- coding: utf-8 -*-
"""
12306-自动抢票
Created on Fri Jan  4 20:49:30 2019

@author: cyj
"""
import base64
import datetime
import json
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from mutagen.mp3 import MP3
import os
import pygame
import re
import random
import sys
import ssl
import socket
import schedule
import threading
import time
import requests

from urllib import parse
import urllib3

from utils.cdnUtils import CDNProxy
from utils.httpUtils import HTTPClient
from utils.sendEmail import SendEmail
from captcha.captcha import Captcha
from selenium import webdriver
from config import urlConf

import logging
import pickle
import yaml
import getpass
import demjson
import psutil

cwd_path = os.path.abspath(os.getcwd())
cfg = yaml.load(open(cwd_path + '/config/conf.yaml','r', encoding='utf-8'))

logger = logging.getLogger(cfg['sys_name'])
logger.setLevel(logging.DEBUG)
# 建立一个filehandler来把日志记录在文件里，级别为debug以上
fh = logging.FileHandler(cfg['log_path'])
fh.setLevel(logging.DEBUG)
# 设置日志格式
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

fh.setFormatter(formatter)
# 将相应的handler添加在logger对象中
logger.addHandler(fh)

urllib3.disable_warnings() #不显示警告信息
ssl._create_default_https_context = ssl._create_unverified_context

httpClient = HTTPClient(0, 0)

req = requests.Session()

is_check_sleep_time = cfg['check_sleep_time']

encoding = cfg['encoding']

captcha_path = cfg['captcha_path']

deviceid_cache_path = cfg['deviceid_cache_path']

seat_type = {'无座': '1', '硬座': '1', '硬卧': '3', '二等卧': 'J','软卧': '4','一等卧': 'I', '高级软卧': '6', '动卧': 'F', '二等座': 'O', '一等座': 'M', '商务座': '9'}

seat_dic = {21: '高级软卧', 23: '软卧', 26: '无座', 28: '硬卧', 29: '硬座', 30: '二等座', 31: '一等座', 32: '商务座', 33: '动卧'}

ticket_type_dic = {'成人票': '1','儿童票': '2','学生票': '3','残军票': '4','成人': '1','儿童': '2','学生': '3','残军': '4'}

webdriver_path = cfg['webdriver_path']

user_agent = cfg['user_agent']

stu_purpose_codes = '0X00'

def conversion_int(str):
    return int(str)

def println(msg):
    print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ': ' + str(msg))
    cmdTxt = 'log:' + str(msg)
    logger.info(msg)
    socketsend(cmdTxt)
    
def log(msg):
    logger.info(msg)
    print(msg)

def getip():
    url = cfg['getip_url']
    headers = {
        'User-Agent': user_agent,
    }
    html = req.get(url, headers=headers, verify=False).content
    ip = re.findall(r'(?<![\.\d])(?:\d{1,3}\.){3}\d{1,3}(?![\.\d])', str(html))
    if ip:
        return ip[0]
    else:
        return ''
    
def string_toTimestamp(str_dt):
    return int(time.mktime(time.strptime(str_dt, "%Y-%m-%d %H:%M")))

class Leftquery(object):
    '''余票查询'''
#    global station_name_res
    def __init__(self):
        self.urls = urlConf.urls
        self.station_url = 'https://kyfw.12306.cn/otn/resources/js/framework/station_name.js'
        self.headers = {
            'Host': 'kyfw.12306.cn',
            'If-Modified-Since': '0',
            'Pragma': 'no-cache',
            'Referer': 'https://kyfw.12306.cn/otn/leftTicket/init',
            'User-Agent': user_agent,
            'X-Requested-With': 'XMLHttpRequest'
        }
        self.station_name_res = None

    def station_name(self, station):
        '''获取车站简拼'''
        if self.station_name_res == None:
#            print('获取车站简拼')
#            print(self.station_url)
            html = None
            try:
               html = req.get(self.station_url, verify=False).text 
            except:
               html = req.get('http://' + server_ip + '/js/station_name.js', verify=False).text 
#            print(html)
            self.station_name_res = html.split('@')[1:]
#            time.sleep(60)
        dict = {}
        for i in self.station_name_res:
            key = str(i.split('|')[1])
            value = str(i.split('|')[2])
            dict[key] = value
        return dict[station]

    def query_by_requests(self, url):
        _urls = {
            "req_url": url,
            "req_type": "post",
            "Referer": "https://kyfw.12306.cn/otn/leftTicket/init",
            "Host": "kyfw.12306.cn",
            "is_logger": False,
            "is_json": True,
            "is_full_url": True,
            're_time': 0.1,
        }
        html = httpClient.send(_urls)
        return html
        
    def query_by_webdriver(self, url):
        try:
            global driver
            if driver==None:
                driver = get_webdriver()
            html = None
            try:
                #driver = webdriver.PhantomJS()
                driver.set_page_load_timeout(5)  
                driver.get(url)
#                js = "window.scrollTo(0,document.body.scrollHeight/3)"  #
#                driver.execute_script(js)
                for cookie in driver.get_cookies():
                    if cookie['name'] == 'RAIL_EXPIRATION' or cookie['name'] == 'RAIL_DEVICEID':
#                        req.cookies[cookie['name']] = cookie['value']
                        httpClient.set_cookie(cookie['name'], cookie['value'])
#                print(driver.page_source)
                html = demjson.decode(driver.find_element_by_tag_name('pre').text)
                
                #print('chrome')
            except BaseException as e:
                driver.get(cfg['index_page'])
                log(e)
            finally:
#                driver.close()
                return html
        except BaseException as ex:
            log(ex)
    
    
    def query(self, n, from_station, to_station, date, cddt_train_types, purpose_codes):
        '''余票查询'''
        fromstation = self.station_name(from_station)
        tostation = self.station_name(to_station)
        self.n = n
        host = 'kyfw.12306.cn'
        if is_core:
            host = real_host
        else:
            if cdn_list:
                host = cdn_list[random.randint(0, len(cdn_list) - 1)]
        if n == 1:
            host = 'kyfw.12306.cn'
        log('[{}]: 余票查询开始，请求主机 --> [{}]'.format(threading.current_thread().getName(), host))
        url = 'https://{}/otn/{}?leftTicketDTO.train_date={}&leftTicketDTO.from_station={}&leftTicketDTO.to_station={}&purpose_codes={}'.format(
            host, left_ticket_path, date, fromstation, tostation, purpose_codes)
#        print(url)
        try:
#            proxie = "{'http': 'http://127.0.0.1:8580'}"
            html = None
            if cfg['enable_webdriver'] and n == -1:
                html = self.query_by_webdriver(url)
            else:
                html = self.query_by_requests(url)
            if html == None or 'data' not in html:
                return
#            print(html)
#            req.cookies['_jc_save_fromStation'] = parse.quote(from_station + ','+ fromstation)
#            req.cookies['_jc_save_toStation'] = parse.quote(to_station + ','+ tostation)
            result = html['data']['result']
            if result == []:
                println('很抱歉,没有查到符合当前条件的列车!')
#                exit()
            else:
                msg = '[' + threading.current_thread().getName() + '] ' + date + ' ' + from_station + '-' + to_station + ' 第[' + str(self.n) + ']次查询成功!'
                log('\n' + '*' * 6 + msg + '*' * 6 + '\n')
                cmdTxt = 'log:' + msg
                try:
                    client.sendall(cmdTxt.encode(encoding))
                except:
                    pass
                # 打印出所有车次信息
                num = 1  # 用于给车次编号,方便选择要购买的车次
                for i in result:
#                    print(i)
                    info = i.split('|')
                    if info[0] != '' and info[0] != 'null':
#                        print(i)
#                        print(str(num) + '.' + info[3] + '车次还有余票:')
#                        println(info[3] + '车次还有余票:')
                        show_flag = False
                        if len(cddt_train_types) == 0:
                            show_flag = True
                        else:   
                            for t in cddt_train_types:
                                if t == info[3][0:1]:
                                    show_flag = True
                                    break
                        if not show_flag:
                            continue
                        ticketInfo = '【' + info[3] + '车次还有余票】: [' + date + '] 出发时间:' + info[8] + ' 到达时间:' + info[9] + ' 历时:' + info[10] + ' '
#                        print(ticketInfo, end='')
                        bl = len(ticketInfo)
#                        from_station_no = info[16]
#                        to_station_no = info[17]
                        for j in seat_dic.keys():
                            if info[j] != '无' and info[j] != '' and info[j] != 0:
                                if info[j] == '有':
                                    ticketInfo = ticketInfo + seat_dic[j] + ':有票 '
#                                    print(seat[j] + ':有票 ', end='')
                                else:
                                    ticketInfo = ticketInfo + seat_dic[j] + ':有' + info[j] + '张票 '
#                                    print(seat[j] + ':有' + info[j] + '张票 ', end='')
                        if len(ticketInfo) > bl:
                            println(ticketInfo)
#                        print('\n')
#                    elif info[1] == '预订':
#                        print(str(num) + '.' + info[3] + '车次暂时没有余票')
#                    elif info[1] == '列车停运':
#                        print(str(num) + '.' + info[3] + '车次列车停运')
#                    elif info[1] == '23:00-06:00系统维护时间':
#                        print(str(num) + '.' + info[3] + '23:00-06:00系统维护时间')
#                    else:
#                        print(str(num) + '.' + info[3] + '车次列车运行图调整,暂停发售')
                    num += 1
            if host in time_out_cdn:
                time_out_cdn.pop(host)
            return result
        except Exception as e:
            if host != 'kyfw.12306.cn' and (str(e).find('timeout') > -1 or str(e).find('timed out') > -1):
                if host in time_out_cdn:
                    time_out_cdn.update({host : int(time_out_cdn[host]) + 1})
                else:
                    time_out_cdn.update({host : 1})
                if int(time_out_cdn[host]) > 2:
                    cdn_list.remove(host)
                println('查询余票信息异常: time out!')
            else:
                flag = False
                if str(e).find('积极拒绝') > -1:
                    flag = True
                    println('查询余票信息异常: 目标计算机积极拒绝，无法连接。')
                if str(e).find('timed out') > -1:
                    flag = True
                    println('查询余票信息异常: time out!')
                if str(e).find('Max retries exceeded') > -1:
                    flag = True
                    println('查询余票信息异常: Max retries exceeded!')
                if flag == False:
                    println('查询余票信息异常: ' + str(e))
#            print(e)
#            exit()



class Login(object):
    '''登录模块'''

    def __init__(self):
#        self.username = username
#        self.password = password
        self.urls = urlConf.urls
        self.url_pic = urlConf.urls['getCodeImg']['req_url']
        self.headers = {
            'Host':'kyfw.12306.cn',
            'Accept' : 'application/json, text/javascript, */*; q=0.01',
            'Origin':'https://kyfw.12306.cn',
            'User-Agent': user_agent,
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Referer': 'https://kyfw.12306.cn/otn/resources/login.html',
            'Accept-Encoding':'gzip, deflate, br',
            'Accept-Language':'zh-CN,zh;q=0.9',
        }

    def showimg(self):
        '''显示验证码图片'''
        global req
        html_pic = req.get(self.url_pic, headers=self.headers, verify=False).content
        open(captcha_path, 'wb').write(html_pic)
        img = mpimg.imread(captcha_path)
        plt.imshow(img)
        plt.axis('off')
        plt.show()

    def captcha(self, answer_num):
        '''填写验证码'''
        answer_sp = answer_num.split(',')
        answer_list = []
        an = {'1': (31, 35), '2': (116, 46), '3': (191, 24), '4': (243, 50), '5': (22, 114), '6': (117, 94),
              '7': (167, 120), '8': (251, 105)}
        for i in answer_sp:
            for j in an.keys():
                if i == j:
                    answer_list.append(an[j][0])
                    answer_list.append(',')
                    answer_list.append(an[j][1])
                    answer_list.append(',')
        s = ''
        for i in answer_list:
            s += str(i)
        answer = s[:-1]
        # 验证验证码
        form_check = {
            'answer': answer,
            'login_site': 'E',
            'rand': 'sjrand',
            '_': str(int(time.time() * 1000))
        }
        html_check = httpClient.send(self.urls['codeCheck'], params=form_check, headers=self.headers)
        try:
            html_check = demjson.decode(html_check)
        except:
            println('验证码校验失败!')
            println(html_check)
            exit()
#        println(html_check)
        if 'result_code' in html_check and html_check['result_code'] == '4':
            println('验证码校验成功!')
            return answer
        else:
            println('验证码校验失败!')
            exit()

    def login(self, username, password, answer):
        '''登录账号'''
        form_login = {
            'username': username,
            'password': password,
            'appid': 'otn',
            'answer':answer
        }
#        resp = req.post(self.url_login, data=form_login, headers=self.headers, verify=False)
        resp = httpClient.send(self.urls['login'], form_login)
#        if resp.status_code != 200:
#            println('登录失败: response ' + str(resp.status_code))
#            return
#        if resp.headers['Content-Type'] == 'text/html':
#            println('登录失败，请稍后重试！')
#            time.sleep(3)
#            return
#        resp = demjson.decode(resp)
        if 'result_code' in resp and resp['result_code'] == 0:
            println('恭喜您, 登录成功!')
        else:
            println('账号、密码或验证码错误, 登录失败!')
            exit()


class Order(object):
    '''提交订单'''

    def __init__(self):
        self.urls = urlConf.urls

    def auth(self):
        auth_res = {'status': True}
        form = {
            '_json_att':''
        }
#        global req
#        resp_checkuser = req.post(self.url_checkuser, data=form, headers=self.head_1, verify=False).json()
#        if resp_checkuser['status'] and resp_checkuser['data']['flag']:
#            return auth_res
        '''验证uamtk和uamauthclient'''
        # 验证uamtk
        form = {
            'appid': 'otn',
            '_json_att':''
        }
#        form = {
#            'appid': 'otn'
#        }
        html_uam = httpClient.send(self.urls['auth'], data=form)
#        if resp_uam.headers['Content-Type'] != 'application/json;charset=UTF-8':
#            auth_res.update({'status': False})
#            return auth_res
#        if resp_uam.status_code != 200:
#            println('验证uam失败: response ' + str(resp_uam.status_code))
#            auth_res.update({'status': False})
#            return auth_res
#        html_uam = json.loads(resp_uam)
        if 'code' in html_uam and html_uam['code'] == 99999:
            println(html_uam['message'])
            auth_res.update({'status': False})
            return auth_res
        if html_uam['result_code'] == 0:
            println('恭喜您,uam验证成功!')
            auth_res.update({'status': True})
        else:
            if html_uam['result_message']:
                println('uam验证失败!' + html_uam['result_message'])
            else:
                println('uam验证失败!')
            auth_res.update({'status': False})
            return auth_res
#            exit()
        # 验证uamauthclient
        tk = html_uam['newapptk']

        form = {
            'tk': tk,
             '_json_att':''
        }
        html_uamclient = httpClient.send(self.urls['uamauthclient'], data=form)
#        println(html_uamclient)
        if html_uamclient !=None and html_uamclient['result_code'] == 0:
            println('恭喜您,uamclient验证成功!')
            auth_res.update({'status': True})
            auth_res.update({'realname': html_uamclient['username']})
        else:
            println('uamclient验证失败!')
            auth_res.update({'status': False})
            return auth_res
        return auth_res
#            exit()

    def checkUser(self):
        check_res = {'status': False}
        form = {
            '_json_att':''
        }
        resp_checkuser =  httpClient.send(self.urls['check_user_url'], data=form)
        if resp_checkuser['status'] and resp_checkuser['data']['flag']:
            check_res.update({'status': True})
        return check_res

    def order(self, result, train_number, from_station, to_station, date):
        '''提交订单'''
        # 用户选择要购买的车次的序号
        secretStr = parse.unquote(result[int(train_number) - 1].split('|')[0])
#        log(secretStr)
        back_train_date = time.strftime("%Y-%m-%d", time.localtime())
        form = {
            'secretStr': secretStr,  # 'secretStr':就是余票查询中你选的那班车次的result的那一大串余票信息的|前面的字符串再url解码
            'train_date': date,  # 出发日期(2018-04-08)
            'back_train_date': back_train_date,  # 查询日期
            'tour_flag': 'dc',  # 固定的
            'purpose_codes': 'ADULT',  # 成人票
            'query_from_station_name': from_station,  # 出发地
            'query_to_station_name': to_station,  # 目的地
            'undefined': ''  # 固定的
        }
        html_order = httpClient.send(self.urls['submit_station_url'], data=form)
#        log(html_order)
#        println(req.cookies)
        if html_order['status'] == True:
            println('提交订单成功！')
            req.cookies['_jc_save_fromDate'] = date;
            req.cookies['_jc_save_toDate'] = datetime.datetime.now().strftime('%Y-%m-%d')
        else:
            msg = '提交订单失败！'
            if  'messages' in html_order:
                msg = msg + html_order['messages'][0]
            println(msg)
        return html_order
#            exit()

    def price(self, is_stu_ticket):
        '''打印票价信息'''
        form = {
            '_json_att': ''
        }

        html_token = httpClient.send(self.urls['initdc_url'], data=form)
        if type(html_token) is not str:
            println('获取票价信息异常！')
            return None
        token = re.findall(r"var globalRepeatSubmitToken = '(.*?)';", html_token)[0]
        leftTicket = re.findall(r"'leftTicketStr':'(.*?)',", html_token)[0]
        key_check_isChange = re.findall(r"'key_check_isChange':'(.*?)',", html_token)[0]
        train_no = re.findall(r"'train_no':'(.*?)',", html_token)[0]
        stationTrainCode = re.findall(r"'station_train_code':'(.*?)',", html_token)[0]
        fromStationTelecode = re.findall(r"'from_station_telecode':'(.*?)',", html_token)[0]
        toStationTelecode = re.findall(r"'to_station_telecode':'(.*?)',", html_token)[0]
        date_temp = re.findall(r"'to_station_no':'.*?','train_date':'(.*?)',", html_token)[0]
        timeArray = time.strptime(date_temp, "%Y%m%d")
        timeStamp = int(time.mktime(timeArray))
        time_local = time.localtime(timeStamp)
        train_date_temp = time.strftime("%a %b %d %Y %H:%M:%S", time_local)
        train_date = train_date_temp + ' GMT+0800 (中国标准时间)'
        train_location = re.findall(r"tour_flag':'.*?','train_location':'(.*?)'", html_token)[0]
        purpose_codes = re.findall(r"'purpose_codes':'(.*?)',", html_token)[0]
        if is_stu_ticket:
            purpose_codes = stu_purpose_codes
#        println('token值:' + token)
#        println('leftTicket值:' + leftTicket)
#        println('key_check_isChange值:' + key_check_isChange)
#        println('train_no值:' + train_no)
        println('stationTrainCode值:' + stationTrainCode)
#        println('fromStationTelecode值:' + fromStationTelecode)
#        println('toStationTelecode值:' + toStationTelecode)
#        println('train_date值:' + train_date)
#        println('train_location值:' + train_location)
        println('purpose_codes值:' + purpose_codes)
        price_list = re.findall(r"'leftDetails':(.*?),'leftTicketStr", html_token)[0]
        # price = price_list[1:-1].replace('\'', '').split(',')
        println('票价:')
        priceInfo = ''
        for i in eval(price_list):
            # p = i.encode('latin-1').decode('unicode_escape')
            priceInfo = priceInfo + i + ' | '
#            print(i + ' | ', end='')
        println(priceInfo)
        return train_date, train_no, stationTrainCode, fromStationTelecode, toStationTelecode, leftTicket, purpose_codes, train_location, token, key_check_isChange

    def passengers(self):
        '''打印乘客信息'''
        return getPassengers()

    def chooseseat(self, ticket_types, passengers, passengers_name, stationTrainCode, cddt_seat, token):
        '''选择乘客和座位'''
        
        choose_type = seat_type[cddt_seat]
        if cddt_seat == '无座' and stationTrainCode.find('D') == 0:
            choose_type = 'O'
        pass_num = len(passengers_name.split(','))  # 购买的乘客数
        pass_list = passengers_name.split(',')
        pass_dict = []
        for i in pass_list:
            info = passengers[int(i) - 1]
#            println(info)
            pass_name = info['passenger_name']  # 名字
            pass_id = info['passenger_id_no']  # 身份证号
            pass_phone = info['mobile_no']  # 手机号码
            all_enc_str = info['allEncStr']
            pass_type = info['passenger_id_type_code']  # 证件类型
            ticket_type = ticket_type_dic[ticket_types[pass_name]] # 车票类型
            dict = {
                'choose_type': choose_type,
                'pass_name': pass_name,
                'pass_id': pass_id,
                'pass_phone': pass_phone,
                'pass_type': pass_type,
                'all_enc_str' : all_enc_str,
                'ticket_type' : ticket_type
            }
            pass_dict.append(dict)

#        num = 0
#        TicketStr_list = []
        passengerTicketStr = ''
        for i in pass_dict:
            TicketStr = i['choose_type'] + ',0,' + i['ticket_type'] + ',' + i['pass_name'] + ',' + i['pass_type'] + ',' + i[
                'pass_id'] + ',' + i['pass_phone'] + ',N,' + i['all_enc_str']
            passengerTicketStr += TicketStr + '_'

        passengerTicketStr = passengerTicketStr[:-1]
#        log(passengerTicketStr)

        num = 0
        passengrStr_list = []
        for i in pass_dict:
            if pass_num == 1:
                passengerStr = i['pass_name'] + ',' + i['pass_type'] + ',' + i['pass_id'] + ',' + i['ticket_type']
                passengrStr_list.append(passengerStr)
            elif num == 0:
                passengerStr = i['pass_name'] + ',' + i['pass_type'] + ',' + i['pass_id'] + ','
                passengrStr_list.append(passengerStr)
            elif num == pass_num - 1:
                passengerStr = '1_' + i['pass_name'] + ',' + i['pass_type'] + ',' + i['pass_id'] + ',' + i['ticket_type']
                passengrStr_list.append(passengerStr)
            else:
                passengerStr = '1_' + i['pass_name'] + ',' + i['pass_type'] + ',' + i['pass_id'] + ','
                passengrStr_list.append(passengerStr)
            num += 1

        oldpassengerStr = ''.join(passengrStr_list)
        if num > 1:
            oldpassengerStr = oldpassengerStr + '_' 
#        println(oldpassengerStr)
        
        form = {
            'cancel_flag': '2',
            'bed_level_order_num': '000000000000000000000000000000',
            'passengerTicketStr': passengerTicketStr,
            'oldPassengerStr': oldpassengerStr,
            'tour_flag': 'dc',
            'randCode': '',
            'whatsSelect': '1',
            'sessionId': '',
            'sig': '',
            'scene': 'nc_login',
            '_json_att': '',
            'REPEAT_SUBMIT_TOKEN': token
        }

        html_checkorder = httpClient.send(self.urls['checkOrderInfoUrl'], data=form)
#        println(html_checkorder)
        if html_checkorder['status'] == True:
            if html_checkorder['data']['submitStatus'] == True:
                println('检查订单信息成功!')
                time.sleep(int(html_checkorder['data']['ifShowPassCodeTime']) / float(1000))
            else:
                println('检查订单信息失败：' + html_checkorder['data']['errMsg'])
        else:
            println('检查订单信息失败：' + html_checkorder['status']['messages'])
#            exit()

        return passengerTicketStr, oldpassengerStr, choose_type

    def leftticket(self, train_tip, train_date, train_no, stationTrainCode, choose_type, fromStationTelecode, toStationTelecode,
                   leftTicket, purpose_codes, train_location, token):
        '''查看余票数量'''
        form = {
            'train_date': train_date,
            'train_no': train_no,
            'stationTrainCode': stationTrainCode,
            'seatType': choose_type,
            'fromStationTelecode': fromStationTelecode,
            'toStationTelecode': toStationTelecode,
            'leftTicket': leftTicket,
            'purpose_codes': purpose_codes,
            'train_location': train_location,
            '_json_att': '',
            'REPEAT_SUBMIT_TOKEN': token
        }

        html_count = httpClient.send(self.urls['getQueueCountUrl'], data=form)
#        println(html_count)
        flag = False
        if html_count['status'] == True:
#            println('查询余票数量成功!')
            ticket = html_count['data']['ticket']
            ticket_split = sum(map(conversion_int, ticket.split(','))) if ticket.find(',') != -1 else ticket
            countT = html_count['data']['countT']
                # if int(countT) is 0:
            println(u'排队成功, 你排在: 第 {1} 位, 该坐席类型还有余票: {0} 张'.format(ticket_split, countT))
            if int(ticket_split) == 0:  
                println('小黑屋新增成员：['+ train_tip + ']')
                ticket_black_list.update({train_tip : ticket_black_list_time })
                flag = False
            else:
                flag = True
#            count = html_count['data']['ticket']
#            println('此座位类型还有余票' + count + '张~')
        else:
            flag = False
            println('检查余票数量失败!')
        return flag
#            exit()


    def confirm(self, passengerTicketStr, oldpassengerStr, key_check_isChange, leftTicket, purpose_codes,
                train_location, choose_seats, token):
        '''最终确认订单'''
        num = 0
        chooseSeatsStr = ''
        for code in choose_seats:
            num += 1
            chooseSeatsStr = chooseSeatsStr + str(num) + code
        form = {
            'passengerTicketStr': passengerTicketStr,
            'oldPassengerStr': oldpassengerStr,
            'randCode': '',
            'purpose_codes': purpose_codes,
            'key_check_isChange': key_check_isChange,
            'leftTicketStr': leftTicket,
            'train_location': train_location,
            'choose_seats': chooseSeatsStr,
            'seatDetailType': '000',
            'whatsSelect': '1',
            'roomType': '00',
            'dwAll': 'N',
            '_json_att': '',
            'REPEAT_SUBMIT_TOKEN': token
        }
        
#        if len(chooseSeatsStr) == 0:
#            form.pop(choose_seats)

        html_confirm = httpClient.send(self.urls['checkQueueOrderUrl'], data=form)
#        println(html_confirm)
        #  {'validateMessagesShowId': '_validatorMessage', 'status': True, 'httpstatus': 200, 'data': {'errMsg': '余票不足！', 'submitStatus': False}
        resDict = {}
        msg = ''
        if html_confirm['status'] == True and html_confirm['data']['submitStatus'] == True:
            resDict.update({'status': True})
#            println('确认购票成功!')
#            return True
            msg = '确认购票成功, 出票中...'
        else:
#            println('确认购票失败: {}'.format(html_confirm['data']['errMsg']))
#            return False
            resDict.update({'status' : False})
            msg = '确认购票失败!'
            if 'data' in html_confirm:
                msg = '确认购票失败: {}'.format(html_confirm['data']['errMsg'])
        resDict.update({'msg' : msg})
        println(msg)
        return resDict
    
    def queryOrderWaitTime(self,token):
        resDict = {}
        resDict.update({'status' : False})
        msg = ''
        try:
            n = 0
            while n < 30:
                n += 1
                println('第[' + str(n) + ']次查询订单状态...')
#                url = self.url_query_waittime + '?random={}&tourFlag=dc&_json_att=&REPEAT_SUBMIT_TOKEN={}'.format(str(int(time.time()*1000)), token)
                html = httpClient.send(self.urls['queryOrderWaitTimeUrl'])
#                println(html)
                if html['status'] and html['data']['queryOrderWaitTimeStatus']:
                    waitTime = html['data']['waitTime']
                    if waitTime == -1:
                        resDict.update({'status' : True})
                        resDict.update({'orderId' : html['data']['orderId']})
                        msg = '占座成功'
                        break
                    elif waitTime == -100:
                        time.sleep(10)
                    elif waitTime < 0:
                        msg = html['data']['msg']
                        break
                    else:
                        time.sleep(int(waitTime))
                else:
                    msg = html['data']['messages']
        except Exception as ex:
            log(ex)
            msg = ex
        resDict.update({'msg' : msg})
        return resDict
    
    
class HBOrder(object):
    '''提交后补订单'''

    def __init__(self):
        self.urls = urlConf.urls
    
    def chechFace(self, secrets, seatTypes):
        resDict = {'status' : True}
        secretList = []
        train_num = 2
        msg = ''
        i = 0
#        url = self.url_passcode.format(random.random())
#        req.get(url, headers=self.head_1, verify=False).content
        while i < len(secrets):
            # chechFace
            secretStr = secrets[i] + '#' + seatTypes[i] +'|'
            form = {
                    'secretList' : secretStr,
                    '_json_att': ''
                }
            json_res = httpClient.send(self.urls['chechFace'], data=form)
#            println(json_res)
            if json_res['status']:
                if json_res['status'] and json_res['data']['face_flag']:
                    form_1 = {
                            'successSecret' : secretStr[:-1],
                            '_json_att': ''
                        }
                    rate_res = httpClient.send(self.urls['getSuccessRate'], data=form_1)
#                    println(secretStr)
#                    println(rate_res)
                    if rate_res['status']:
                        if rate_res['data']['flag'] == '':
                            msg = rate_res['data']['msg']
                        else:   
                            if len(secretList) < train_num:
                                secretList.append(secretStr)
                                r_flag = rate_res['data']['flag'][0]
                                msg = '{}: {}, {}; '.format(r_flag['start_train_date'],r_flag['train_no'], r_flag['info'])
                            else:
                                break  
                    else:
                        resDict.update({'status' : False})
                        msg = rate_res['messages'][0]
                else:
                    resDict.update({'msg' : json_res['messages'][0]})
            else:
                resDict.update({'status' : False})
                msg = json_res['messages'][0]
                if msg.find('已有待支付') > -1:
                    break
            i += 1
        if len(secretList) == 0:
            resDict.update({'status' : False})
        resDict.update({'msg' : msg})
        resDict.update({'secretList' : secretList})
        return resDict
    
    
    def submitOrderRequest(self, secretList):
        '''提交候补订单'''
        secretStr = ''.join(secretList)
        secretStr = secretStr[:-1]
        form = {
                'secretList' : secretStr,
                '_json_att': ''
            }
        json_res = httpClient.send(self.urls['SubmitOrderRequestRsp'], data=form)
        if json_res['status']:
            println('提交候补订单成功！')
        else:
            msg = '提交候补订单失败！'
            if  'messages' in json_res:
                    msg = msg + json_res['messages'][0]
            println(msg)
        return json_res['status'];
    
    
    def initApi(self, passengers):
#        flag = True
        resDict = {'status' : True}
#        flag = self.viewUrl(self.url_conf)['status']
#        if flag:
        resDict.update({'pass' : passengers})
        init_res = self.viewUrl(self.urls['passengerInitApi'])
        if init_res['status']:
            jzParam = init_res['data']['jzdhDateE'] + '#' +init_res['data']['jzdhHourE'].replace(':', '#')
            resDict.update({'jzParam' : jzParam})
            resDict.update({'hbTrainList' : init_res['data']['hbTrainList']})
#        resDict.update({'status' : flag})
        return resDict
    
    
    def getQueueNum(self):
        '''获取排队序号'''
        json_res = httpClient.send(self.urls['getQueueNum'])
#        log(json_res)
        if json_res['status'] and json_res['data']['flag']:
            msg = '候补排队成功！'
            for q in json_res['data']['queueNum']:
                msg = msg + '车次[{}], 排队信息：{}; '.format(q['station_train_code'], q['queue_info'])
            println(msg)
            return True
        else:
            println(json_res['messages'][0])
            return False
            
    def confirmHB(self, passengers, hbTrainList, jzParam, bkInfo):
        '''乘车人'''
        passengers_name = ''
        ticket_types = {}
        for n in range(len(bkInfo.passengers_name)):
            name = bkInfo.passengers_name[n]
            tt = '成人票'
            if len(bkInfo.ticket_types) > n:
                tt = bkInfo.ticket_types[n]
            if tt not in ticket_type_dic:
                tt = '成人票'
            ticket_types.update({name : tt})
            p_idx = 1
            for p in passengers:
#                            log(p)
                if name == p['passenger_name']:
                    passengers_name = passengers_name + str(p_idx) + ','
                    break
                else:
                   p_idx += 1
        passengers_name = passengers_name[:-1]
        
        pass_list = passengers_name.split(',')
        pass_dict = []
        for i in pass_list:
            info = passengers[int(i) - 1]
#            println(info)
            pass_name = info['passenger_name']  # 名字
            pass_id = info['passenger_id_no']  # 身份证号
            pass_phone = info['mobile_no']  # 手机号码
            all_enc_str = info['allEncStr']
            pass_type = info['passenger_id_type_code']  # 证件类型
            ticket_type = ticket_type_dic[ticket_types[pass_name]] # 车票类型
            dict = {
                'pass_name': pass_name,
                'pass_id': pass_id,
                'pass_phone': pass_phone,
                'pass_type': pass_type,
                'all_enc_str' : all_enc_str,
                'ticket_type' : ticket_type
            }
            pass_dict.append(dict)
        
        # 拼接passengerInfo
        passengerInfo = ''
        for p in pass_dict:
            passengerInfo = passengerInfo + '{}#{}#1#{}#{};'.format(p['ticket_type'],p['pass_name'],p['pass_id'],p['all_enc_str'])
        
        hbTrain = ''
        for hbt in hbTrainList:
            hbTrain = hbTrain + hbt['train_no'] + ',' + hbt['seat_type_code'] + '#'
            
        form = {
                'passengerInfo' : passengerInfo,
                'jzParam' : jzParam,
                'hbTrain' : hbTrain,
                'lkParam' : ''
            }
        json_res = httpClient.send(self.urls['confirmHB'], data=form)
        if json_res['status']:
            println('确认候补订单成功！')
        else:
            println(json_res['messages'][0])
        return json_res['status']
    
    def queryQueue(self):
        resDict = ({'status' : False})
        msg = ''
        try:
            n = 0
            while n < 30:
                n += 1
                println('第[' + str(n) + ']次查询候补订单状态...')
                html = httpClient.send(self.urls['queryQueue'])
#                println(html)
                if html['status']:
                    status = html['data']['status']
                    waitTime = 0.1
                    if 'waitTime' in html['data']:
                        waitTime = html['data']['waitTime']
                    if status == 1:
                        resDict.update({'status' : True})
#                        resDict.update({'orderId' : html['data']['orderId']})
                        msg = '候补成功'
                        break
                    elif waitTime == -100:
                        time.sleep(3)
                    elif waitTime < 0:
                        msg = html['data']['msg']
                        break
                    else:
                        time.sleep(int(waitTime) + 0.5)
                else:
                    msg = html['data']['messages']
        except Exception as ex:
            log(ex)
            msg = ex
        resDict.update({'msg' : msg})
        return resDict
        
    
    def viewUrl(self, url):
        json_res = httpClient.send(url)
        if json_res['status']:
            pass
        else:
            println(json_res['messages'][0])
        return json_res
        
    
class Cancelorder(Login, Order):
    '''取消订单'''

    def __init__(self):
        Login.__init__(self)
        Order.__init__(self)
        self.url_ordeinfo = 'https://kyfw.12306.cn/otn/queryOrder/queryMyOrderNoComplete'
        self.url_cancel = 'https://kyfw.12306.cn/otn/queryOrder/cancelNoCompleteMyOrder'
        self.head_cancel = {
            'Host': 'kyfw.12306.cn',
            'Referer': 'https://kyfw.12306.cn/otn/queryOrder/initNoComplete',
            'User-Agent': user_agent,
        }

    def orderinfo(self):
        '''查询未完成订单'''
        form = {
            '_json_att': ''
        }
        global req
        res = {'status': False}
        html_orderinfo = req.post(self.url_ordeinfo, data=form, headers=self.head_cancel, verify=False).json()
#        println(html_orderinfo)
        if html_orderinfo['status'] == True:
#            println('查询未完成订单成功!')
            try:
                n = 0
                while True and n < 36:
                    if 'orderCacheDTO' in html_orderinfo['data']:
                        n += 1
                        orderCacheDTO = html_orderinfo['data']['orderCacheDTO']
#                        print(orderCacheDTO)
                        if 'waitTime' in orderCacheDTO:
                            t = int(orderCacheDTO['waitTime'])
                            if t >= 0:
                                time.sleep(t + 8)
                            else:
                                if orderCacheDTO['status'] != 1 and 'message' in orderCacheDTO:
                                    res.update({'status' : False})
                                    res.update({'msg' : orderCacheDTO['message']['message']})
                                else:
                                    res.update({'status' : False})
                                    res.update({'msg' : '查询未完成订单异常！'})
                                return res
                            try:
                                html_orderinfo = req.post(self.url_ordeinfo, data=form, headers=self.head_cancel, verify=False).json()
#                                print(html_orderinfo)
                                println('第[' + str(n) + ']次查询订单状态...')
                            except:
                                pass
                        else:
                            time.sleep(10)
                    if 'orderDBList' in html_orderinfo['data']:
                        break
                if 'orderDBList' in html_orderinfo['data']:  
                    order_info = html_orderinfo['data']['orderDBList'][0]
                    pass_list = order_info['array_passser_name_page']
                    sequence_no = order_info['tickets'][0]['sequence_no']
                    train_date = order_info['start_train_date_page']
                    from_station = order_info['from_station_name_page'][0]
                    to_station = order_info['to_station_name_page'][0]
                    log('订单详情:')
                    oInfo = train_date, from_station, to_station, pass_list, sequence_no
                    println(oInfo)
                    res.update({'status' : True})
                    res.update({'sequence_no' : sequence_no})
                    res.update({'start_train_date_page' : order_info['start_train_date_page']})
                    res.update({'msg' : '获取未完成订单成功！'})
                else:
                    if 'orderCacheDTO' in html_orderinfo['data']:
                        res.update({'status' : True})
                        res.update({'msg' : '下单成功，系统正在为您分配坐席...'})
                    else:             
                        res.update({'status' : False})
                        res.update({'msg' : '您没有未完成的订单！'})              
#                return sequence_no
            except Exception as e:
                res.update({'status' : False})
                res.update({'msg' : '查询未完成订单异常！'})
                println(e)
#                exit()
        else:
            res.update({'msg' : '查询未完成订单失败！'})
        return res
#            exit()

    def confirmcancel(self, sequence_no):
        '''确认取消订单'''
        print('\n')
        i = input('是否确定取消该订单?(Y or N):')
        if i == 'Y' or i == 'y':
            form = {
                'sequence_no': sequence_no,  # 订单号('EF20783324')
                'cancel_flag': 'cancel_order',  # 固定
                '_json_att': ''
            }
            global req
            html_cancel = req.post(self.url_cancel, data=form, headers=self.head_cancel, verify=False).json()
            print(html_cancel)
            if html_cancel['status'] == True:
                print('取消订单成功!')
            else:
                print('取消订单失败!')
        else:
            print('退出取消订单程序...')
#            exit()


def pass_captcha():
    '''自动识别验证码'''
    println('正在识别验证码...')
    global req
#    url_pic = 'https://kyfw.12306.cn/passport/captcha/captcha-image64?login_site=E&module=login&rand=sjrand&0.15905700266966694'
    url_captcha = 'http://littlebigluo.qicp.net:47720/'
#    headers = {
#        'Host': 'kyfw.12306.cn',
#        'Referer': 'https://kyfw.12306.cn/otn/resources/login.html',
#        'User-Agent': user_agent,
#    }
#    res = req.get(url_pic, headers=headers, verify=False)
    rep_json = httpClient.send(urlConf.urls['getCodeImg1'])
    i = 1
    while rep_json == None:
        if i > 5:
            break
        i += 1
        time.sleep(2)
        rep_json = httpClient.send(urlConf.urls['getCodeImg1'])
        if 'image' not in rep_json:
            continue
    if 'image' not in rep_json:
        return ''
    base64_str = rep_json['image']
#    print(base64_str)
    html_pic = base64.b64decode(base64_str)
#    print(html_pic)
    open(captcha_path, 'wb').write(html_pic)
    
    # 采用本地识别算法
    if cfg['captcha_mode'] == 'local':
        captcha = Captcha()
        return captcha.main(captcha_path)
    
    files = {
        'pic_xxfile': open(captcha_path, 'rb')
    }
    headers = {
        'Referer': url_captcha,
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': user_agent
    }
    try:
        return pass_captcha_360(base64_str)
    except:
#        log(e)
        try:
            res = req.post(url_captcha, files=files, headers=headers, verify=False).text
            result = re.search('<B>(.*?)</B>', res).group(1).replace(' ', ',')
            return result 
        except:
            println('Sorry!验证码自动识别网址已失效~')
    #        exit()

def pass_captcha_360(img_buf):
    url_get_check = 'http://60.205.200.159/api'
    url_img_vcode = 'http://check.huochepiao.360.cn/img_vcode'
    headers1 = {
        'Content-Type': 'application/json',
        'Referer': 'http://60.205.200.159/',
        'User-Agent': user_agent
    }
    headers2 = {
        'Referer': 'https://pc.huochepiao.360.cn/',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': user_agent
    }
    form1 = {
        'base64': img_buf,
    }
    global req
    json_check = req.post(url_get_check, data=json.dumps(form1), headers=headers1, timeout=2, verify=False).json()
#    print(json_check)
    form2 = {
        '=': '',
        'img_buf': img_buf,
        'type': 'D',
        'logon': 1,
        'check':json_check['check']
    }
    json_pass_res = req.post(url_img_vcode, data=json.dumps(form2), headers=headers2, verify=False).json()
    log(json_pass_res)
    an = {'1': (31, 35), '2': (116, 46), '3': (191, 24), '4': (243, 50), '5': (22, 114), '6': (117, 94),
              '7': (167, 120), '8': (251, 105)}
    pass_res = json_pass_res['res'].split('),(')
#    print(pass_res)
    res = ''
    for group in pass_res:
        point = group.replace('(', '').replace(')', '').split(',')
        min_key = '1'
        min_val = sys.maxsize
        for key in an:
            d = pow(an[key][0] - int(point[0]), 2) + pow(an[key][1] - int(point[1]), 2)
            if d < min_val:
                min_val = d
                min_key = key
        if len(res) > 0:
            res = res + ','
        res = res + min_key
#    print(res)
    if len(res) == 0:
        return None
    return res
                
def order(bkInfo):
    '''订票函数'''
    res = {'status': False}
    # 用户输入购票信息:
#    from_station = input('请输入您要购票的出发地(例:北京):')
#    to_station = input('请输入您要购票的目的地(例:上海):')
#    date = input('请输入您要购票的乘车日期(例:2018-03-06):')
    from_station = bkInfo.from_station
    to_station = bkInfo.to_station
    dates = bkInfo.dates
    # 余票查询
    query = Leftquery()
    # 提交订单
    order = None
    n = 0
    avg_time = -1
    purpose_codes = 'ADULT'
    stu_flag = False
    for _type in bkInfo.ticket_types:
        if _type.find('学生') < 0:
            stu_flag = False
            break
        else:
            stu_flag = True
    if stu_flag:
        purpose_codes = stu_purpose_codes
    while res['status'] != True:
        check_sleep_time('抢票任务挂起中')
        if len(bkInfo.expired) > 0 and string_toTimestamp(bkInfo.expired) < int(time.time()):
            println('[' + threading.current_thread().getName() + ']: 抢票任务已过期，当前线程退出...')
            res['status'] = True
            break
        info_key = bkInfo.uuid + '-' + from_station + '-' + to_station
        if thread_list[info_key] == False:
            cddt_trains.pop(info_key)
            booking_list.pop(info_key)
            println('[' + threading.current_thread().getName() + ']: 抢票任务发生变动，当前线程退出...')
            res['status'] = True
            break
        if booking_list[info_key] == True:
            try_count[info_key] += n
            res['status'] = True
            break
        n += 1
        if is_core:
            global sleep_base
            sleep_base = cfg['core_sleep_base']
        st = round(random.uniform(sleep_base + 0.2 * len(booking_list), sleep_base + (7 - int(bkInfo.rank)) / 2), 2)
        if bkInfo.is_sell_mode:
            st = cfg['sell_mode_sleep_time']
            print('*****当前订单为起售抢票模式*****')
#        st = 0
#        if len(cdn_list) < 3:
#            st = 1
#        st = round(st + random.uniform(0.5, len(booking_list)), 2)
        avg_time = (avg_time == -1) and st or (avg_time + st) / 2
        print('平均[' + str(round(avg_time,2)) + ']秒查询一次,下次查询[' + str(st) + ']秒后...')
        time.sleep(st)
        t_no = ''
        p_name = ''
        for date in dates:
            try:
                is_exec_query = check_sell_time(bkInfo.is_sell_mode, date, bkInfo.sell_time)
                delay = cfg.get('sell_mode_delay_time', 2)
                if is_exec_query[0] is False:
                    n -= 1
                    println('日期【{}】的起售时间未到，本次查询结束，下一查询计划自动延长[{}]秒~'.format(date, delay))
                    time.sleep(delay)
                    continue
                if bkInfo.is_sell_mode and is_exec_query[0] and is_exec_query[1] >= cfg.get('sell_mode_exp_time', 30):
                    println('车票已发售[{}]分钟，系统自动切入普通抢票模式，本次余票查询延长[{}]秒~'.format(is_exec_query[1], delay))
                    time.sleep(delay)
                # 防止多次多线程并发封禁ip
                lock.acquire()
                str_now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                global last_req_time
                if last_req_time == str_now:
                    time.sleep(round(random.uniform(0.1, (7 - int(bkInfo.rank)) / 2), 2))
                last_req_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                lock.release()
#                print('[' + threading.current_thread().getName() + '] '+ last_req_time + ': 余票查询开始...')
                result = query.query(n, from_station, to_station, date, bkInfo.cddt_train_types, purpose_codes)
                if result == None:
                    n -= 1
                    continue
                # 用户选择要购买的车次的序号
                '''判断候选车次'''
                cddt_seat_keys = []
#                cddt_seat_types = {}
                for cddt_seat in bkInfo.candidate_seats:
                    for k in seat_dic.keys():
                        if seat_dic[k] == cddt_seat:
                            cddt_seat_keys.append(k)
#                            cddt_seat_types.update({ k : seat_type[cddt_seat] })
                            break
                trains_idx = []
                hb_trains_idx = {}
                temp_trains_idx = []
                num = 1
                for i in result:
                    info = i.split('|')
                    if info[0] != '' and info[0] != 'null':
                        pTxt = ''
                        for train in bkInfo.candidate_trains:
                            seat_flag = False
                            hb_flag = False
                            seat_tp = ''
                            for sk in cddt_seat_keys:
                                if info[38].find(seat_type[seat_dic[sk]]) < 0:
                                    # 可以候补
                                    seat_tp = seat_type[seat_dic[sk]]
                                    hb_flag = True
#                                if info[sk] != '无' and info[sk] != '' and (info[38] == '' or str(info[38]).find(cddt_seat_types[sk]) < 0):
                                if info[sk] != '无' and info[sk] != '' and info[sk] != '*':
#                                    log(info[3] + info[sk])
                                    if info[sk] == '有' or int(info[sk]) >= len(bkInfo.passengers_name):
                                        seat_flag = True
                                    break
                            if seat_flag or (cfg['enable_hb'] and hb_flag):
                                t_tip  = date + '-' + from_station + '-' + to_station + '-' + info[3]
                                if t_tip in ticket_black_list:
                                    temp = '['+ t_tip +']属于小黑屋成员，小黑屋剩余停留时间：' + str(ticket_black_list[t_tip]) + 's'
                                    if pTxt != temp:
                                        pTxt = temp
                                        println(temp)
                                    
                                else:
                                    sot = info[8].split(':') 
                                    art = info[9].split(':')
                                    tsp = info[10].split(':')
                                    t1 = int(sot[0]) * 60 + int(sot[1])
                                    t3 = int(art[0]) * 60 + int(art[1])
                                    ts = int(tsp[0]) * 60 + int(tsp[1])
                                    now = datetime.datetime.now()
                                    departure = date == now.strftime('%Y-%m-%d')
                                    t5 = now.hour * 60 + now.minute + free_time
                                    if (t3-t1) < ts or (departure and t5 > t1):
                                        continue
                                    if info[3] == train:
                                        if seat_flag:
                                            trains_idx.append(num)
                                        else:
#                                            print(num)
#                                            print(seat_tp)
                                            hb_trains_idx.update({num : seat_tp})
                                    else:
                                        # 出发时间和到达时间符合要求的也可
                                        if len(bkInfo.min_set_out_time) > 0 and len(bkInfo.max_arrival_time) > 0:
                                            msot = bkInfo.min_set_out_time.split(':')
                                            mart = bkInfo.max_arrival_time.split(':')
                                            t2 = int(msot[0]) * 60 + int(msot[1])
                                            t4 = int(mart[0]) * 60 + int(mart[1])
                                            # 保证在区间内
                                            if t1 >= t2 and t3 <= t4:
                                                if seat_flag:
                                                    temp_trains_idx.append(num)
                                                else:
                                                    hb_trains_idx.update({num : seat_tp})                      
                    num += 1
                if temp_trains_idx:
                    trains_idx.extend(temp_trains_idx)
                if len(trains_idx) > 0 or (cfg['enable_hb'] and len(hb_trains_idx) > 0 ):
                    
                    lock.acquire()
#                    if booking_now[bkInfo.group] > int(bkInfo.rank):
                    if booking_now[bkInfo.group] != 0:
                        time.sleep(1)
                    else:
                        booking_now[bkInfo.group] = int(bkInfo.rank)
                    lock.release()
                    order = Order()
                    auth_res = order.auth()
                    loginOut = False
                    while auth_res['status'] != True or auth_res['realname'] != bkInfo.realname:
                        if auth_res['status'] == True:
                            # 先退出当前登录账号
                            httpClient.send(urlConf.urls['loginOut'])
                            loginOut = True
                            # 进入下一次循环
                        if loginOut and 'realname' in auth_res and auth_res['realname'] != bkInfo.realname:
                            log('登录账号用户姓名与配置文件不一致，请检查！')
                            break
                        # 填写验证码
                        login = Login()
                        get_rail_deviceid()
                        answer_num = pass_captcha()         
                        if answer_num == None:
                            time.sleep(3)
#                            answer_num = input('请填入验证码(序号为1~8,中间以逗号隔开,例:1,2):')
                            continue
#                       print(answer_num)
                        answer = login.captcha(answer_num)
                        login.login(bkInfo.username, bkInfo.password, answer)
                        auth_res = order.auth()
                    dump(httpClient,req_cache_path)
                    
                # 判断候补
                hb_id = '{}-{}-{}-{}'.format(bkInfo.passengers_name, date, from_station, to_station)
                if hb_id not in hb_finish_list and len(trains_idx) == 0 and cfg['enable_hb'] and len(hb_trains_idx) > 0:
                    hb_trains = []
                    hb_seats = []
                    for hbt_idx in hb_trains_idx.keys():
                        hb_trains.append(result[int(hbt_idx) - 1].split('|')[0])
                        hb_seats.append(hb_trains_idx[hbt_idx])
                    hbOrder = HBOrder()
                    # 乘车人
                    passengers = getPassengers()
                    if passengers == None:
                        continue
                    ckf_res = hbOrder.chechFace(hb_trains, hb_seats)
                    if ckf_res['status']:
                        submit_res = hbOrder.submitOrderRequest(ckf_res['secretList'])
                        if submit_res:
                            init_res = hbOrder.initApi(passengers)
                            if init_res['status'] and hbOrder.getQueueNum():
                                confirm_res = hbOrder.confirmHB(init_res['pass'],init_res['hbTrainList'],init_res['jzParam'], bkInfo)
                                if confirm_res:
                                    qq_res = hbOrder.queryQueue()
                                    if qq_res['status']:
                                        hb_finish_list.update({hb_id : True})
                                        # 发送邮件通知
                                        println('恭喜您，候补抢票成功！')
                                        subject = '自助订票系统--订票成功通知'
                                        success_info = '<div>主机[' + local_ip + ']通知：恭喜您，车票候补成功，请及时支付！</div><div style="color: #000000; padding-top: 5px; padding-bottom: 5px; font-weight: bold;"><div>订单信息如下：</div>'
                                        success_info = success_info + ','.join(bkInfo.passengers_name) + ' ' + date + '，' + from_station + '-->' + to_station + '。</div>'
                                        success_info = success_info + '<div><p>---------------------<br/>From: 12306 PABS<br/>' + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '</p><div>'
                                        email = SendEmail()
                                        send_res = email.send(bkInfo.email, subject, success_info)
                                        playaudio(cfg['finish_task_audio'], cfg['loop_play'])
                                        if send_res == False:
                                            playaudio(cfg['post_failed_audio'], cfg['loop_play'])
                                            println('正在尝试使用邮件代理发送...')
                                            cmdTxt = 'addmailtask:' + bkInfo.email + '|' + subject + '|' + success_info
                                            try:
                                                client.sendall(cmdTxt.encode(encoding))
                                                bytes.decode(client.recv(1024), encoding)
                                            except:
                                                pass 
                    else:
                        println(ckf_res['msg'])
                for train_idx in trains_idx:
                    t_no = result[int(train_idx) - 1].split('|')[3]
                    train_tip = date + '-' + from_station + '-' + to_station + '-' + t_no
                    # 如果在黑名单中，不抢票
                    if train_tip in ticket_black_list:
                        #println('['+ train_tip +']属于小黑屋成员，本次放弃下单，小黑屋剩余停留时间：' + str(ticket_black_list[train_tip]) + 's')
                        continue
                    println('正在抢 ' + date + '：[' + t_no + ']次 ' + from_station + '--->' + to_station)
                    train_number = train_idx
                    # 提交订单
                    passengers = order.passengers()  # 打印乘客信息
                    if passengers == None:
                        continue
#                    c_res = order.checkUser()
                    o_res = order.order(result, train_number, from_station, to_station, date)
                    if o_res['status'] is not True and 'messages' in o_res:
                        if o_res['messages'][0].find('有未处理的订单') > -1 or o_res['messages'][0].find('未完成订单') > -1  or o_res['messages'][0].find('行程冲突') > -1 :
                            println('您的账户[' + bkInfo.username + ']中有未完成订单，本次任务结束。')
                            subject = '自助订票系统--任务取消通知'
                            success_info = '<div>主机[' + local_ip + ']通知：您的账户[' + bkInfo.username + ']中有未完成订单，请在12306账号[未完成订单]中处理，本次任务结束。</div><div style="color: #000000; padding-top: 5px; padding-bottom: 5px; font-weight: bold;"><div>当前抢票任务信息如下：</div>'
                            success_info = success_info + '[' + date + '，' + from_station + '-->' + to_station + '，' + t_no + '次列车]</div>'
                            success_info = success_info + '<div><p>---------------------<br/>From: 12306 PABS<br/>' + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '</p><div>'
                            email = SendEmail()
                            send_res = email.send(bkInfo.email, subject, success_info)
                            playaudio(cfg['finish_task_audio'], cfg['loop_play'])
                            if send_res == False:
                                println('正在尝试使用邮件代理发送...')
                                cmdTxt = 'addmailtask:' + bkInfo.email + '|' + subject + '|' + success_info
                                try:
                                    client.sendall(cmdTxt.encode(encoding))
                                    resp = bytes.decode(client.recv(1024), encoding)
                                except:
                                    pass
                            booking_list[info_key] = True
                            break
                    # 检查订单
                    content = order.price(stu_flag)  # 打印出票价信息
                    if content is None:
                        continue
                    # 选择乘客和座位
                    '''乘车人'''
                    passengers_name = ''
                    p_name = ''
                    ticket_types = {}
                    for n in range(len(bkInfo.passengers_name)):
                        name = bkInfo.passengers_name[n]
                        tt = '成人票'
                        if len(bkInfo.ticket_types) > n:
                            tt = bkInfo.ticket_types[n]
                        if tt not in ticket_type_dic:
                            tt = '成人票'
                        ticket_types.update({name : tt})
                        p_idx = 1
                        for p in passengers:
#                            log(p)
                            if name == p['passenger_name']:
                                passengers_name = passengers_name + str(p_idx) + ','
                                p_name = p_name + p['passenger_name']+'(' + p['passenger_id_no'] + ')' + ', '
                                break
                            else:
                               p_idx += 1
                    passengers_name = passengers_name[:-1]
                    p_name = p_name[:-1]
#                    passengers_name = input('请选择您要购买的乘客编号(例:1,4):')
#                    choose_seat = input('请选择您要购买的座位类型(例:商务座):')
#                    print(passengers_name)
                    cddt_seats = []
                    for seat in bkInfo.candidate_seats:
                        for idx in seat_dic:
                            t_num = result[int(train_idx) - 1].split('|')[idx]
                            if seat_dic[idx] == seat and t_num != '无' and t_num != '':
                                cddt_seats.append(seat)
                                break
                    for seat in cddt_seats:
                        choose_seat = seat
#                        print(choose_seat)
                        pass_info = order.chooseseat(ticket_types, passengers, passengers_name, content[2], choose_seat, content[8])
                        # 查看余票数
#                        print('查看余票')
                        left_res =  order.leftticket(train_tip, content[0], content[1], content[2], pass_info[2], content[3], content[4], content[5], content[6],
                                         content[7], content[8])
                        # 是否确认购票
                        # order.sure()
                        # 最终确认订单
#                        res = {'status': left_res}
#                        if left_res:
                        res = order.confirm(pass_info[0], pass_info[1], content[9], content[5], content[6], content[7], bkInfo.choose_seats, content[8])
                        
                        if res['status']:
                            res = order.queryOrderWaitTime(content[8])
#                            cancelorder = Cancelorder()
#                            res = cancelorder.orderinfo()
                            if res['status'] != True:
                                println(res['msg'])
                                res.update({'msg' : res['msg']})
                            if 'code' in res and res['code'] == 99999:
                                res['status'] = False
                                res.update({'msg' : res['message']})
                                continue
                            if res['msg'].find('余票不足') > -1 or res['msg'].find('没有足够的票') > -1:
                                println('[' + seat + ']下单异常：余票不足！')
                                res['status'] = False
                                continue
                        if res['status']:
                            booking_list[info_key] = res['status']
                            println('恭喜您，抢票成功！')
                            subject = '自助订票系统--订票成功通知'
                            success_info = '<div>主机[' + local_ip + ']通知：恭喜您，车票预订成功，请及时支付！</div><div style="color: #000000; padding-top: 5px; padding-bottom: 5px; font-weight: bold;"><div>订单信息如下：</div>'
                            success_info = success_info + '订单号码：' + res['orderId'] + '，' + p_name + ' ' + date + '，' + from_station + '-->' + to_station + '，' + t_no + '次列车，' + choose_seat +'。</div>'
                            success_info = success_info + '<div><p>---------------------<br/>From: 12306 PABS<br/>' + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '</p><div>'
                            email = SendEmail()
                            send_res = email.send(bkInfo.email, subject, success_info)
                            playaudio(cfg['finish_task_audio'], cfg['loop_play'])
                            if send_res == False:
                                playaudio(cfg['post_failed_audio'], cfg['loop_play'])
                                println('正在尝试使用邮件代理发送...')
                                cmdTxt = 'addmailtask:' + bkInfo.email + '|' + subject + '|' + success_info
                                try:
                                    client.sendall(cmdTxt.encode(encoding))
                                    bytes.decode(client.recv(1024), encoding)
                                except:
                                    pass 

                            break
                        else:
                            if res['msg'].find('余票不足') > -1 or res['msg'].find('排队人数现已超过余票数') > -1:
                                println('小黑屋新增成员：['+ train_tip + ']')
                                ticket_black_list.update({train_tip : ticket_black_list_time })
                    if res['status']:
                        break
                    lock.acquire()
                    booking_now[bkInfo.group] = 0
                    lock.release()
            except Exception as e:
                log('['+ datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') +']: 本次下单异常...')
                log(e)
                raise
                if train_tip:  
                    println('小黑屋新增成员：['+ train_tip + ']')
                    ticket_black_list.update({train_tip : ticket_black_list_time })
        
def run(bkInfo):
#    print('1.购票  2.取消订单  3.退票')
#    print('*' * 69)
#    func = input('请输入您要操作的选项(例:1):')
    global username, password
    username = bkInfo.username
    password = bkInfo.password
    println('当前购票账号：' + username)
    flag = False
    n = 0
    while flag == False and n < 5:
        try:
            order(bkInfo)
            flag = True
        except BaseException as ex:
            raise
            log(ex)
            n += 1
            time.sleep(3)
            flag = False
            println('第【'+ str(n) +'】次失败重试中...')
           
class BookingInfo(object):
    def __init__(self, booking):
        self.booking = booking
        # 账号
        self.uuid = booking['bno'] + '-' + booking['dates']
        
        self.group = booking['group']
        
        self.realname = booking['realname']
        
        self.username = booking['username']
        
        # 密码
        self.password = booking['password']
        # 出发点
        self.from_station = booking['from_station']
        # 目的地
        self.to_station = booking['to_station']
        # 乘车日期
        self.dates = booking['dates'].split(',')
        # 乘车人姓名
        self.passengers_name = booking['passengers_name'].split(',')
        # 车票类型
        self.ticket_types = booking['ticket_types'].split(',')
        # 候选车次
        self.candidate_trains = booking['candidate_trains'].split(',')
        # 候选坐席类别
        self.candidate_seats = booking['candidate_seats'].split(',')
        # 选座
        self.choose_seats = []
        if len(booking['choose_seats']) > 0:
            self.choose_seats = booking['choose_seats'].split(',')
        # 邮箱
        self.email = booking['email']
        # 线程数
        self.rank = booking['rank']
        # 最早出发时间
        self.min_set_out_time = booking['set_out']
        # 最晚到达时间
        self.max_arrival_time = booking['arrival']
        # 任务过期时间
        self.expired = booking['expired']
        # 火车类型['G','D','K']
        self.cddt_train_types = booking['cddt_train_types'].split(',')
        # 是否起售抢票模式
        self.is_sell_mode = False
        if 'is_sell_mode' in booking:
            self.is_sell_mode = booking['is_sell_mode']
        # 起售时间
        self.sell_time = ''
        if 'sell_time' in booking:
            self.sell_time = booking['sell_time']

def playaudio(path, loop_play = False):
    try:
        pygame.mixer.init()
        println('开始播放音乐：' + path)
        pygame.mixer.music.load(path)
        audio = MP3(path)
        while True:
            pygame.mixer.music.play()
            time.sleep(audio.info.length)
            if loop_play == False:
                break
#        time.sleep(12)
        pygame.mixer.music.stop()
    except Exception as e:
        log(e)
        
#    client.send(cmdTxt.encode(encoding))
#    thread = threading.Thread(target=socketsend,name='Thread-Socket-Send',args=(cmdTxt,))
#    thread.start()
def socketsend(data):
    try:
        global client
        client.sendall(data.encode(encoding))
        bytes.decode(client.recv(1024), encoding)
    except Exception as e:
        logger.error(e)
#        print(e)
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            client.connect((server_ip, 12306))
        except:
            logger.error('尝试重连失败！')
            print('尝试重连失败！')
def keepalive():
    try:  
        time_task()
        socketsend(str(time.time()))
    except:
        pass

def task():
    check_sleep_time('系统将在06:00以后继续扫描抢票任务')
    println('扫描抢票任务开始...')
    global local_ip
    local_ip = getip()
    c_jobs = []
    filename=cfg['booking_filename']
    try:
        println('get canceltask...')
        clt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        clt.connect((server_ip, 12306))
        clt.send('getcanceltask'.encode(encoding))
        resp = bytes.decode(clt.recv(1024), encoding)
        if resp.startswith('taskinfo'):
            resp = resp[9:].replace('\n','|')
            if len(resp) > 0:
                log('获取取消抢票任务信息成功！')
                c_jobs = resp.split('|')
#                if cancel_key in jobs:
#                    flag = True
#                    thread_list.update({info_key : False})
#                    println('取消抢票任务-->' + info_key)
#                    cmdTxt = 'delcanceltask:' + jobs[0]
#                    client.sendall(cmdTxt.encode(encoding))
            else:
                log('未发现取消抢票任务...')
        else:
            log('未发现取消抢票任务...')
        if task_src == 'net':
            log('获取服务器共享抢票任务...')
                # 检查是否有退出任务
            f_name = cfg['net_booking_filename']
            clt.send(('getfile:' + cfg['booking_filename']).encode(encoding))
            while True:
                resp = bytes.decode(clt.recv(1024), encoding)
                if resp.startswith('Content-Length:'):
                    clt.send(resp[15:].encode(encoding))
                    resp = clt.recv(int(resp[15:]))
                    with open(f_name, 'wb') as fp:
                        fp.write(resp)
                    log('获取服务器共享抢票任务成功！')
                    break
            if os.path.exists(f_name):
                filename = f_name
        clt.close()
    except:
        pass
    bks = yaml.load(open(cwd_path + '/' + filename,'r', encoding='utf-8'))
    bookings = bks['bookings']
    for booking in bookings:
        if booking['is_work']== False :
            continue
        bkInfo = BookingInfo(booking)
#        run(bkInfo)
        info_key = bkInfo.uuid + '-' + bkInfo.from_station + '-' + bkInfo.to_station
        str_dates = ''
        for d in bkInfo.dates:
            str_dates = d + ','
        str_dates = str_dates[:-1]
        cancel_key = bkInfo.username + '-' + str_dates + '-' + bkInfo.group
#        print(bkInfo.uuid)
        flag = False
        for key in booking_list:
#            print(key)
            if key == info_key:
                flag = True
                break
        if cancel_key in c_jobs:
            flag = True
            thread_list.update({info_key : False})
            println('取消抢票任务-->' + info_key)
        if len(bkInfo.expired) > 0 and string_toTimestamp(bkInfo.expired) < int(time.time()):
            flag = True
            thread_list.update({info_key : False})
            println('任务过期，取消任务-->' + info_key)
        cddt_tra_flag = False
        for key in cddt_trains:
#            print(key)
            if key == info_key:
                cddt_tra_flag = True
                break
        if cddt_tra_flag:
            # 存在则判断是否有变动
            if cddt_trains[info_key] != booking['dates']:
                # 停止原线程
                thread_list.update({info_key : False})
        else:
            cddt_trains.update({info_key : booking['dates']})
        if flag == False:
            println('添加抢票任务-->' + info_key)
            booking_list.update({info_key : False})
            
            try_count.update({info_key : 0})
    #        ptint(booking_list)
            i = 0
#            t_num = int(bkInfo.rank)
            t_num = 1
            while i < t_num:
                thread = threading.Thread(target=run,name='Thread-'+str((len(thread_list)) * t_num + i +1),args=(bkInfo,))
                thread.start()
                thread_list.update({info_key : True})
                booking_now.update({bkInfo.group : 0})
                i += 1
                time.sleep(round(1 + random.uniform(0, 1), 2))
    # 移除已经删除的任务线程
    for info_key in thread_list:
        if info_key not in booking_list:
            thread_list.update({info_key : False})

def cdn_req(cdn):
    for i in range(len(cdn)):
        http = HTTPClient(0, 0)
        urls = {
            'req_url': '/otn/login/init',
            'req_type': 'get',
            'Referer': 'https://kyfw.12306.cn/otn/index/init',
            'Host': 'kyfw.12306.cn',
            're_try': 0,
            're_time': 0.1,
            's_time': 0.1,
            'is_logger': False,
            'is_test_cdn': True,
            'is_json': False,
        }
        http._cdn = cdn[i].replace("\n", "")
        start_time = datetime.datetime.now()
        rep = http.send(urls)
        if type(rep) != str:
            continue
        if (datetime.datetime.now() - start_time).microseconds / 1000 < 500:
            # 如果有重复的cdn，则放弃加入
            if cdn[i].replace("\n", "") not in cdn_list:
                cdn_list.append(cdn[i].replace("\n", ""))
    for to_cdn in time_out_cdn:
        # 移除超时次数大于n的cdn
        if time_out_cdn[to_cdn] > 3 and to_cdn in cdn_list:
            cdn_list.remove(to_cdn)
            time_out_cdn[to_cdn] = 0
#    println(time_out_cdn)
    println(u"所有cdn解析完成, 目前可用[" + str(len(cdn_list)) + "]个")
#    # 回写可用
#    CDN = CDNProxy()
#    CDN.write_cdn_file(cdn_list)

def cdn_certification():
    """
    cdn 认证
    :return:
    """
    CDN = CDNProxy()
    all_cdn = CDN.open_cdn_file()
    if all_cdn:
        # print(u"由于12306网站策略调整，cdn功能暂时关闭。")
        println(u"开启cdn查询")
        println(u"本次待筛选cdn总数为{}".format(len(all_cdn)))
        t = threading.Thread(target=cdn_req, args=(all_cdn,))
        t.setDaemon(True)
        # t2 = threading.Thread(target=self.set_cdn, args=())
        t.start()
        # t2.start()
    else:
        raise Exception(u"cdn列表为空，请先加载cdn")
def cdn_upd():
    CDN = CDNProxy()
    t = threading.Thread(target=CDN.update_cdn_list, args=())
    t.setDaemon(True)
    # t2 = threading.Thread(target=self.set_cdn, args=())
    t.start()
            
def time_task():
#    lock.acquire()
    for t in ticket_black_list:
#        print(ticket_black_list[t])
        ticket_black_list[t] = ticket_black_list[t] - timespan
        if ticket_black_list[t] < 1:
            println('[{}]离开小黑屋'.format(t))
            ticket_black_list.pop(t)
            break
#    lock.release()

def check_sleep_time(msg):

    while is_check_sleep_time and True:
        now = datetime.datetime.now()
        if (now.hour == 23 and now.minute >= 30) or now.hour < 6:
            print('['+ datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') +']: 当前时间处于12306网站维护时段，{}...'.format(msg))
            time.sleep((60 - now.minute) * 60 - now.second + 5)
        else:
            break
        
'''序列化'''
def dump(obj, path):
    with open(path,'wb') as f:
        pickle.dump(obj,f)

'''反序列化'''        
def load_obj(path):
    obj = None
    if os.path.exists(path) == False:
        return obj
    try:
        with open(path,'rb') as f:
            obj=pickle.load(f)
    except:
        pass
    return obj

def login_sys():
    order = Order()
    auth_res = order.auth()
    uname = None
    pwd = None
    while auth_res['status'] != True:
        if uname == None:  
            uname =input('请输入12306账号：')
            pwd = getpass.getpass('请输入12306密码：')
        login = Login()
        get_rail_deviceid()
        login.showimg()
        answer_num = input('请填入验证码(序号为1~8,中间以逗号隔开,例:1,2):')
        answer = login.captcha(answer_num)
        login.login(uname, pwd, answer)
        auth_res = order.auth()
    dump(httpClient,req_cache_path)

def get_left_ticket_path():
    global req
    global left_ticket_path
    init_url = 'https://kyfw.12306.cn/otn/leftTicket/init'
    headers = {
        'Host': 'kyfw.12306.cn',
        'User-Agent': user_agent
    }
    html = req.get(init_url, headers=headers, verify=False).text
    ltp = re.findall(r'var CLeftTicketUrl = \'(.*?)\';', str(html))
    if ltp:
        left_ticket_path = ltp[0]
    else:
        left_ticket_path = 'leftTicket/queryA'

def kill_all_chromedriver():
    try:
        pids = psutil.pids()
        for pid in pids:
            p = psutil.Process(pid)
            if p.name() == 'chromedriver.exe':
                 os.popen('taskkill.exe /pid:' + str(pid))
    except:
         pass


def get_chrome_deviceid():
    kill_all_chromedriver()
    global driver
    if driver == None:
        driver = get_webdriver()
    _device = {}
    try:    
        driver.get(cfg['index_page'])
        time.sleep(2)
        url = 'https://kyfw.12306.cn/otn/{}?leftTicketDTO.train_date={}&leftTicketDTO.from_station=BJP&leftTicketDTO.to_station=JNK&purpose_codes=ADULT'.format(
                left_ticket_path, datetime.datetime.now().strftime('%Y-%m-%d'))
        driver.get(url)
        time.sleep(3)
        for cookie in driver.get_cookies():
            if cookie['name'] == 'RAIL_EXPIRATION' or cookie['name'] == 'RAIL_DEVICEID':
#                    req.cookies[cookie['name']] = cookie['value']
                _device.update({cookie['name'] : cookie['value']})
    except:
        pass
    return _device
def getPassengers():
    '''打印乘客信息'''
    # 确认乘客信息
    form = {
        '_json_att': ''
    }
    # getPassCodeNew
    html_pass = httpClient.send(urlConf.urls['get_passengerDTOs'], data=form)
    if 'data' not in html_pass:
        return None
    passengers = html_pass['data']['normal_passengers']
    return passengers

def get_rail_deviceid():
    # 读取本地
    _device = load_obj(deviceid_cache_path)
    deviceid_key = 'RAIL_DEVICEID'
    exp_key = 'RAIL_EXPIRATION'
    if _device != None:
        if exp_key in _device:
            n = int(time.time() * 1000)
            exp = int(_device.get(exp_key))
            if exp > n:
                return _device
            else:
                _device = None
        else:
            _device = None 
    if _device == None:
        if cfg['enable_webdriver']:
            # 从chrome获取
            _device = get_chrome_deviceid()
        else:
            # 从配置文件获取
            _device = {
                        deviceid_key : cfg[deviceid_key],
                        exp_key : cfg[exp_key]
                 }
    if _device != None and len(_device) > 1:
        dump(_device, deviceid_cache_path)
        # set
        if req != None:
            req.cookies[deviceid_key] = _device.get(deviceid_key)
            req.cookies[exp_key] = _device.get(exp_key)
        if httpClient != None:
            httpClient.set_cookie(deviceid_key, _device.get(deviceid_key))
            httpClient.set_cookie(exp_key, _device.get(exp_key))
    return _device
'''
校验是否达到起售时间
'''
def check_sell_time(is_sell_mode, book_date, sell_time):
    _days = 30
    if 'sell_after_day' in cfg:
        try:
            _days = int(cfg['sell_after_day'])
        except:
            pass
    _days = _days - 1
    flag = False
    # 开售了多久了，minute
    over_time = 30
    # 订票日期时间戳
    book_date_stamp = int(time.mktime(time.strptime(book_date, '%Y-%m-%d'))) 
    # 今日可抢票日期
    sell_date = (datetime.date.today() + datetime.timedelta(days = _days)) 
    sell_date_stamp = int(time.mktime(sell_date.timetuple()))
    # 抢票日期
    if book_date_stamp <= sell_date_stamp:
        flag = True
    if is_sell_mode is False:
        return flag, over_time
    # 起售时间
    if type(sell_time) is str and len(sell_time) == 5:
        now = datetime.datetime.now()
        nt = now.hour * 3600 + now.minute * 60 + now.second
        st = int(sell_time.split(':')[0]) * 3600 + int(sell_time.split(':')[1]) * 60 - 3
        flag = nt > st
        over_time = int((nt-st)/60)
    return flag, over_time
    
def get_webdriver():
    try:
        return webdriver.Chrome(webdriver_path)
    except:
        return webdriver.Chrome()

global booking_list
global cddt_trains
global thread_list
global try_count
global booking_now
global client
global local_ip
global left_ticket_path

cdn_list = []
time_out_cdn = {}
ticket_black_list = {}
hb_finish_list = {}
last_req_time = None
lock = threading.Lock()

ticket_black_list_time = cfg['ticket_black_list_time']
keep_alive_time = cfg['keep_alive_time']
timespan = cfg['timespan']
free_time = cfg['free_time']
sleep_base = cfg['sleep_base']
task_src = cfg['task_src']
server_ip = cfg['server_ip']
server_port = cfg['server_port']
req_cache_path = cfg['req_cache_path']
is_core = cfg['is_core']
real_host = cfg['real_host']
enable_hb = cfg['enable_hb']
driver = None


if __name__ == '__main__':

    try:
        httpClient = load_obj(req_cache_path)
        if httpClient == None:
            httpClient = HTTPClient(0, 0)
        if cfg['auto_captcha'] == False:
            login_sys()
        check_sleep_time('系统将在06:00以后继续抢票')
        get_left_ticket_path()
        get_rail_deviceid()
        log('*' * 30 + '12306自动抢票开始' + '*' * 30)
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        client.connect((server_ip, 12306))
        booking_list = {}
        cddt_trains = {}
        thread_list = {}
        try_count = {}
        booking_now = {}
        local_ip = getip()

        cdn_certification()
    
        task()
        schedule.every(10).minutes.do(task)
        if is_core is False:
            schedule.every(30).minutes.do(cdn_upd)
        schedule.every(60).minutes.do(cdn_certification)
        schedule.every(timespan).seconds.do(time_task)
        while True: 
            schedule.run_pending()
            time.sleep(1)
        client.close()
    except Exception as ex:
        log(ex)
    
