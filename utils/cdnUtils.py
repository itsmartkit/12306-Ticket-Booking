# -*- coding: utf-8 -*-
"""
cdn_utils
Created on Fri Jan  4 20:49:30 2019

@author: cyj
"""
import datetime
import demjson
import os
import re
import sys
import time
import threading
import requests
import ssl
import json

ssl._create_default_https_context = ssl._create_unverified_context
req = requests.Session()

try:
    reload(sys)
    sys.setdefaultencoding('utf-8')
except NameError:
    pass

class CDNProxy:
    def __init__(self):
#        self.host = host
        self.httpClint = requests
        self.ping_encode = ['']
        self.city_list = []
        self.timeout = 3

    def _set_header(self):
        """设置header"""
        return {
            'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36',
            'Accept': '*/*',
            'X-Requested-With': 'XMLHttpRequest',
        }
    def println(self, msg):
        print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ': ' +msg)
    def get_city_id(self):
        """
        获取所有城市md5参数
        :return:
        """
        try:
            url = 'http://ping.chinaz.com/kyfw.12306.cn'
            data = {'host': 'ping.chinaz.com', 'lintType': '电信,多线,联通,移动'}
            rep = self.httpClint.post(url, data, headers=self._set_header(), timeout = self.timeout)
            html = bytes.decode(rep.content)
            self.ping_encode = re.findall(re.compile(r'id="enkey" value=\"(\S+)\"'), html)
            city_re = re.compile(r'<div id=\"(\S+)\" class=\"row listw tc clearfix')
            self.city_list = re.findall(city_re, html)
            if self.city_list:
                self.println('请求成功，获取到[{}]个探测点。'.format(len(self.city_list)))
            return self.city_list
        except Exception as e:
            print(e)
#            print(e)
            pass
    def update_cdn_list(self):
        """
        更新cdn列表
        """
        self.println('开始更新cdn列表...')
        cdn_list = []
        
        # ping.chinaz.com
        self.ping_chinaz(cdn_list)
        
        # ping.aizhan.com
        self.ping_aizhan(cdn_list)
        
        # tools.ipip.net
        self.ping_ipip(cdn_list)
        
        # www.wepcc.com
        self.ping_wepcc(cdn_list)
        
        # update cdn file
        cdn_list = list(set(cdn_list))
        self.update_cdn_file(cdn_list)
        
        #write cdn file
        cdn.write_cdn_file(cdn.open_cdn_file())
        

    def ping_chinaz(self, cdn_list):
        self.println('[ping.chinaz.com] 分析cdn开始...')
        city_id = self.get_city_id()
        for guid in city_id:      
            url = 'http://ping.chinaz.com/iframe.ashx?t=ping&callback=jQuery111304824429956769827_{}'.format(int(round(time.time() * 1000)))
            data = {'guid': guid,
                    'encode': self.ping_encode[0],
                    'host': 'kyfw.12306.cn',
                    'ishost': 0,
                    'checktype': 0
                }
            try:
                
                rep = self.httpClint.post(url, data, headers=self._set_header(), timeout = self.timeout)
                text = bytes.decode(rep.content)
                res = re.findall(re.compile(r'[(](.*?)[)]', re.S), text)
#                print(res)
                if res:    
                    jsonRes = demjson.decode(res[0])
#                    print(jsonRes)
                    if jsonRes['state'] == 1:
                        ip = jsonRes['result']['ip']
                        if ip not in cdn_list:
                            cdn_list.append()
#                        print(jsonRes['result']['ip'])
            except:
#                print(e)
                pass
        self.println('[ping.chinaz.com] 分析cdn完毕！')
        return cdn_list

    def ping_aizhan(self, cdn_list):
        self.println('[ping.aizhan.com] 分析cdn开始...')
        url_index = 'https://ping.aizhan.com/'
        url = 'https://ping.aizhan.com/api/ping?callback=flightHandler'
        headers = {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3833.0 Safari/537.36',
                'Accept': '*/*',
                'Host': 'ping.aizhan.com',
                'Referer': 'https://ping.aizhan.com/',
                'X-Requested-With': 'XMLHttpRequest',
            }
        try:
            html =bytes.decode(req.get(url_index).content)
            _csrf = re.findall('_csrf:\'(.*?)\'', html)
            data = {'type': 'ping',
                'domain': 'kyfw.12306.cn',
                '_csrf': _csrf[0]
           }
            rep = req.post(url, data, headers=headers, timeout = 10)
            text = bytes.decode(rep.content)
            text = text.replace('flightHandler(','')[:-1]
            json_callback = json.loads(text);
            for r in json_callback:
                cdn_list.append(json_callback[r]['ip'])
            self.println('[ping.aizhan.com] 分析cdn完毕！')
        except:
            pass
     
    def ping_ipip(self, cdn_list):
        self.println('[tools.ipip.net] 分析cdn开始...')
        url = 'https://tools.ipip.net/ping.php?v=4&a=send&host=kyfw.12306.cn&area%5B%5D=china'
        headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3833.0 Safari/537.36',
                'Accept': '*/*',
                'Host': 'tools.ipip.net',
                'Referer': 'https://tools.ipip.net/ping.php'
            }
        try:
            rep = req.get(url, headers=headers, timeout = 60)
            text = bytes.decode(rep.content)
            ip_re = re.compile(r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b')
            hosts = re.findall(ip_re,text);
            hosts = list(set(hosts));
            for ip in hosts:  
                cdn_list.append(ip)
            self.println('[tools.ipip.net] 分析cdn完毕！')
        except:
            pass
        
    def ping_wepcc(self, cdn_list):
        self.println('[www.wepcc.com] 分析cdn开始...')
        url_index = 'https://www.wepcc.com/'
        ping_url = 'https://www.wepcc.com/check-ping.html'
        headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3833.0 Safari/537.36',
                'Accept': '*/*',
                'Host': 'www.wepcc.com',
                'Referer': 'https://www.wepcc.com/'
            }
        try:
            node = '1,2,3,4'
            data = {
                    'node': node,
                    'host': 'kyfw.12306.cn',
                }
            rep = req.post(url_index, data, headers=headers, timeout = 10)
            text = bytes.decode(rep.content)
            data_ids = re.findall(r'<tr class="item" data-id="(\d{1,})">',text)
            for i in data_ids:
                try:
                    data = {
                        'node': i,
                        'host': 'kyfw.12306.cn',
                    }
                    rep = req.post(ping_url, data, headers=headers, timeout = 3).json()
    #                    text = bytes.decode(rep.content)
                    cdn_list.append(rep['data']['ip'])
                except:
                    pass
            self.println('[www.wepcc.com] 分析cdn完毕！')
        except:
            pass

    def update_cdn_file(self, cdn_list):
        if cdn_list:
            cdn_file = self.open_cdn_file()
            path = os.path.join(os.path.dirname(__file__), '../cdn_list')
            try:
                f = open(path, 'a')
                n = 0
                for ip in cdn_list:
                    if ip not in cdn_file:
#                        print('write' + ip)
                        f.write(ip + '\n')
                        n += 1
                f.close()
                self.println('更新cdn列表完毕，新增[{}]个。'.format(n))
            except:
                pass
    def open_cdn_file(self):
        cdn = []
        # cdn_re = re.compile("CONNECT (\S+) HTTP/1.1")
        # path = os.path.join(os.path.dirname(__file__), '../cdn_list')
        # with open(path, "r") as f:
        #     for i in f.readlines():
        #         # print(i.replace("\n", ""))
        #         cdn_list = re.findall(cdn_re, i)
        #         if cdn_list and "kyfw.12306.cn:443" not in cdn_list:
        #             print(cdn_list[0].split(":")[0])
        #             cdn.append(cdn_list[0].split(":")[0])
        #     return cdn
        path = os.path.join(os.path.dirname(__file__), '../cdn_list')
        with open(path, 'r') as f:
            for i in f.readlines():
                # print(i.replace("\n", ""))
                if i and 'kyfw.12306.cn:443' not in i:
                    cdn.append(i.replace('\n', ''))
            return cdn
    def write_cdn_file(self, cdn_list):
        cdn_list_path = os.path.join(os.path.dirname(__file__), '../cdn_list')
        url_cdn_path = os.path.join(os.path.dirname(__file__), '../url_cdn_list')
        if os.path.exists(url_cdn_path):
            with open(url_cdn_path, 'r') as f:
                for i in f.readlines():
                    # print(i.replace("\n", ""))
                    if i and 'kyfw.12306.cn:443' not in i:
                        cdn_list.append(i.replace('\n', '')[7:-4])
        cdn_list = list(set(cdn_list))
        cdn_list.sort(reverse=True)
#        temp_cdn_path = os.path.join(os.path.dirname(__file__), '../temp_cdn_list')
        f = open(cdn_list_path, 'w')
        for ip in cdn_list:
            if len(ip) > 0:
                f.write(ip + '\n')
        f.close()
#        os.remove(cdn_list_path)
#        os.rename(temp_cdn_path, cdn_list_path)
        
if __name__ == '__main__':
    cdn = CDNProxy()
    t = threading.Thread(target=cdn.update_cdn_list(), args=())
    t.setDaemon(True)
    t.start()