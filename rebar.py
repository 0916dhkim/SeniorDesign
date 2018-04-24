from math import sqrt, pi
diameter = {}
area = {}

min_num = 3
max_num = 11

for ii in range(min_num, 8+1):
    diameter[ii] = ii/8.000
    area[ii] = pi * diameter[ii]**2 / 4

for ii in range(9, max_num+1):
    area[ii] = ((ii-1)/8) ** 2
    diameter[ii] = 2 * sqrt(area[ii]/pi)


def fit_bars(area_req, width, aggregate_size):
    count = {}
    fail = {'bar': max_num, 'count': 0}

    # Find the required number of bars to achieve required area.
    for bar_num in range(min_num, max_num+1):
        req_num = int(area_req // area[bar_num] + 1)
        count[bar_num] = req_num

    # Find the configuration with the least reinforcement area.
    ret = fail
    for bar_num in range(min_num, max_num+1):
        if count[bar_num] < 2:
            count[bar_num] = 2

        if width >= diameter[bar_num]*count[bar_num]+aggregate_size*(count[bar_num]-1):
            if ret['count'] is 0 or area[ret['bar']]*ret['count'] > area[bar_num]*count[bar_num]:
                ret = {'bar': bar_num, 'count': count[bar_num]}

    return ret