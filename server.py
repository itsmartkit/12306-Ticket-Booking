# -*- coding: utf-8 -*-
"""
Created on Mon Jan  7 17:58:42 2019

@author: cyj
"""


import threading
import socket
import datetime
import os
import uuid
import codecs

encoding = 'utf-8'
BUFSIZE = 1024
mt_path = '/usr/local/nginx/html/mailtask/'
log_path = '/usr/local/nginx/html/log/'
ct_path = '/usr/local/nginx/html/canceltask/'
# a read thread, read data from remote
class Reader(threading.Thread):
    def __init__(self, client):
        threading.Thread.__init__(self)
        self.client = client
        
    def run(self):
        while True:
            data = self.client.recv(BUFSIZE)
            if(data):
                msg = bytes.decode(data, encoding)
#                print('[' + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '] client', self.client.getpeername(), msg)
                if msg.startswith('addmailtask'):  
                    if not os.path.exists(mt_path):
                        os.makedirs(mt_path)
                    write(mt_path + str(uuid.uuid1()) + '.txt', msg[12:])
                if msg.startswith('log'):
                    if not os.path.exists(log_path):
                        os.makedirs(log_path)
                    log(log_path + datetime.datetime.now().strftime('%Y%m%d%H') + '.txt', '['+ datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') +' client' + str(self.client.getpeername()) + ']: ' + msg[4:])
                if msg.startswith('delmailtask'):
                    delfile(mt_path + msg[12:])
                if msg.startswith('getmailtask'):
                    self.client.sendall(getmailtask().encode(encoding))
                # 取消任务
                if msg.startswith('delcanceltask'):
                    delfile(ct_path + msg[14:])
                if msg.startswith('getcanceltask'):
                    if not os.path.exists(ct_path):
                        os.makedirs(ct_path)
                    self.client.sendall(getcanceltask().encode(encoding))
                if msg.startswith('getfile'):
                    if not os.path.exists(msg[8:]):
                        info = '# file does not exist'
                        self.client.sendall(('Content-Length:' + str(len(info))).encode(encoding))
                        data = self.client.recv(BUFSIZE)
                        self.client.sendall(info.encode(encoding))
                    else:
                        getfile(self.client, msg[8:])
                else:
                    self.client.sendall('success'.encode(encoding))
            else:
                break
        print("close:", self.client.getpeername())
        
#    def readline(self):
#        rec = self.inputs.readline()
#        if rec:
#            string = bytes.decode(rec, encoding)
#            if len(string)>2:
#                string = string[0:-2]
#            else:
#                string = ' '
#        else:
#            string = False
#        return string

def getmailtask():
    task = 'taskinfo:'
    try:
#        file_dir = '/usr/local/nginx/html/mailtask/'
        for root, dirs, files in os.walk(mt_path):
            for file in files:
                task =  task + file
                fp = codecs.open(mt_path + file,'r', encoding='UTF-8')
                line = fp.readline()
                fp.close()
                task = task+ '|' + line
                break
        print('获取邮件发送任务成功！')
    except Exception as e:
        print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '：获取邮件发送任务异常！')
        print(e)
        pass
    
    return task

def getcanceltask():
    task = 'taskinfo:'
    try:
#        file_dir = '/usr/local/nginx/html/mailtask/'
        for root, dirs, files in os.walk(ct_path):
            for file in files:
                task =  task + file
                fp = codecs.open(ct_path + file,'r', encoding='UTF-8')
                line = fp.readline()
                fp.close()
                task = task+ '|' + line
                break
        print('获取取消抢票任务成功！')
    except Exception as e:
        print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '：获取取消抢票任务异常！')
        print(e)
        pass
    return task

def getfile(conn, fullpath):
    try:
        conn.sendall(('Content-Length:' + str(os.path.getsize(fullpath))).encode(encoding))
        conn.recv(BUFSIZE)
        with open(fullpath, 'rb') as f:
            conn.sendall(f.read())
    except Exception as e:
        info = '# ' + str(e).replace('\n',' ')
        conn.sendall(('Content-Length:' + str(len(info))).encode(encoding))
        conn.recv(BUFSIZE)
        conn.sendall(info.encode(encoding))
        pass

def delfile(fullpath):
    try:
        os.remove(fullpath)
        print('成功删除文件：' + fullpath)
    except Exception as e:
        print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '：文件删除失败！')
        print(e)
        pass
    

def write(fullpath, content):
    try:
#        print(fullpath)
        fp = open(fullpath,'a',encoding='utf-8')
#        content = content.replace('log:','\n' + (' ' * 56))
        content = (content + '\n').encode('utf-8','ignore').decode('utf-8')
        fp.write(content);
        if not fullpath.startswith(log_path):     
            print('成功写入文件：' + fullpath)
    except Exception as e:
        print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '：文件写入失败！')
        print(e)
        pass

def log(fullpath, content):
    try:
#        print(fullpath)
        fp = open(fullpath,'a',encoding='gbk')
        content = content.replace('log:','\n' + (' ' * 56))
        content = (content + '\n').encode('gbk','ignore').decode('gbk')
        fp.write(content);
        if not fullpath.startswith(log_path):     
            print('成功写入文件：' + fullpath)
    except Exception as e:
        print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '：文件写入失败！')
        print(e)
        pass

# a listen thread, listen remote connect
# when a remote machine request to connect, it will create a read thread to handle
class Listener(threading.Thread):
    def __init__(self, port):
        threading.Thread.__init__(self)
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("0.0.0.0", port))
        self.sock.listen(5)
    def run(self):
        print("listener started")
        while True:
            client, cltadd = self.sock.accept()
            Reader(client).start()
            cltadd = cltadd
            print("accept a connect")
 
lst  = Listener(12306)   # create a listen thread
lst.start() # then start