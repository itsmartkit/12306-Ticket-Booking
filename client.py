# -*- coding: utf-8 -*-
"""
Created on Thu Jan 10 09:21:53 2019

@author: cyj
"""

import datetime
import time
import schedule
import socket

from utils.sendEmail import SendEmail

encoding = 'utf-8'
#client.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

def println(msg):
    print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ': ' + msg)

#def socketsend(data):
#    client.sendall(data.encode(encoding))
#    bytes.decode(client.recv(1024), encoding)
    
#def keepalive():
#    while True:
#        socketsend(str(time.time()))
#        time.sleep(keep_alive_time)
def run():
    try:    
        while True:
            now = datetime.datetime.now()
            if now.hour > 22 or now.hour < 6:
                print('['+ datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') +']: 当前时间处于12306网站维护时段，任务将在06:00以后继续...')
                time.sleep((60 - now.minute) * 60 - now.second + 5)
            else:
                break
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(('39.95.20.xxx', 12306))
        println('get mailtask...')
        client.send('getmailtask'.encode(encoding))
        resp = bytes.decode(client.recv(1024), encoding)
        if resp.startswith('taskinfo'):
            resp = resp[9:]
    #        println('server response: ' + resp)
            if len(resp) > 0:
                print('获取邮件代发任务成功！')
                mailInfo = resp.split('|')
                email = SendEmail()
                send_res = email.send(mailInfo[1], mailInfo[2], mailInfo[3])
                if send_res:
                    cmdTxt = 'delmailtask:' + mailInfo[0]
                    client.sendall(cmdTxt.encode(encoding))
                    println('server response: ' + bytes.decode(client.recv(1024), encoding))
            else:
                print('未发现邮件代发任务...')
#        time.sleep(10)
        client.close()
    except Exception as e:
#        raise
        print(e)
        pass
    
keep_alive_time = 2 # 保活任务，单位s

if __name__ == '__main__':
    email = SendEmail()
#    t = threading.Thread(target=keepalive, args=())
#    t.setDaemon(True)
#    t.start()
#    schedule.every(2).seconds.do(keepalive)
    schedule.every(30).seconds.do(run)
    print('定时任务已启动...')
    while True:
        schedule.run_pending()
        time.sleep(1)