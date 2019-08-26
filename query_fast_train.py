# -*- coding: utf-8 -*-
"""
Created on Fri Aug 23 11:24:41 2019

@author: Administrator
"""
import main

from_station = '北京'
to_station = '济南'
date = '2019-08-25'
set_out = '14:00'  #最早出发时间
arrival = '22:00'  #最晚到达时间
cddt_seats = '二等座'
cddt_train_types = 'G'
# 最长历时
max_trip_time = 110



if __name__ == '__main__':
    
    query = main.Leftquery()
    result = query.query(1, from_station, to_station, date, cddt_train_types)
    if result:
        fast_train = ''
        for info_str in result:
            info = info_str.split('|')
            seats = cddt_seats.split(',')
            ignore = False
            for seat in seats:
                if info[38].find(main.seat_type[seat]) > -1:
                    ignore = True
                    break
            if ignore:
                continue
            msot = set_out.split(':')
            mart = arrival.split(':')
            sot = info[8].split(':') 
            art = info[9].split(':')
            tsp = info[10].split(':')
            t1 = int(sot[0]) * 60 + int(sot[1])
            t2 = int(msot[0]) * 60 + int(msot[1])
            t3 = int(art[0]) * 60 + int(art[1])
            t4 = int(mart[0]) * 60 + int(mart[1])
            ts = int(tsp[0]) * 60 + int(tsp[1])
            # 保证在区间内
            if ts <=  max_trip_time and t1 >= t2 and t3 <= t4 and (t3-t1) >= ts:
                if len(fast_train) > 0:
                    fast_train = fast_train + ','
                fast_train = fast_train + info[3]
        print(fast_train)