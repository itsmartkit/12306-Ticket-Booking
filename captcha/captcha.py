# coding: utf-8
import sys

import cv2
import numpy as np
from keras import models

from captcha import pretreatment
from captcha.mlearn_for_image import preprocess_input

class Captcha(object):
    
    def get_text(self,img, offset=0):
        text = pretreatment.get_text(img, offset)
        text = cv2.cvtColor(text, cv2.COLOR_BGR2GRAY)
        text = text / 255.0
        h, w = text.shape
        text.shape = (1, h, w, 1)
        return text


    def main(self,fn):
        # 读取并预处理验证码
        img = cv2.imread(fn)
        text = self.get_text(img)
        imgs = np.array(list(pretreatment._get_imgs(img)))
        imgs = preprocess_input(imgs)
    
        res_text = []
    
        # 识别文字
        model = models.load_model('captcha/model.h5')
        label = model.predict(text)
        label = label.argmax()
        fp = open('captcha/texts.txt', encoding='utf-8')
        texts = [text.rstrip('\n') for text in fp]
        text = texts[label]
        res_text.append(text)
    #    print(text)
        # 获取下一个词
        # 根据第一个词的长度来定位第二个词的位置
        if len(text) == 1:
            offset = 27
        elif len(text) == 2:
            offset = 47
        else:
            offset = 60
        text = self.get_text(img, offset=offset)
        if text.mean() < 0.95:
            label = model.predict(text)
            label = label.argmax()
            text = texts[label]
    #        print(text)
            res_text.append(text)
        
        # 加载图片分类器
        model = models.load_model('captcha/12306.image.model.h5')
        labels = model.predict(imgs)
        labels = labels.argmax(axis=1)
        res = ''
        for pos, label in enumerate(labels):
            for txt in res_text:
                if txt == texts[label]:
                    res= res + ',' + str(pos // 4 * 4 + pos % 4 + 1)
    #        print(pos // 4, pos % 4, texts[label])
        return res[1:]

if __name__ == '__main__':
    captcha = Captcha()
    print(captcha.main('../captcha.jpg'))
