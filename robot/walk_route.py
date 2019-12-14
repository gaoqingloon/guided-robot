"""
    pip install future
"""
import json
import requests

# Du config
Du_AK = "zspWrePa3M6jwZYDfXFWnKp6rHBSwXj7"


def save_route_points(ori, des, save_file):
    """
    ori: 起点(纬度，经度)
    des: 终点(纬度，经度)
    """

    ori_lng, ori_lat = ori.split(",")
    des_lng, des_lat = des.split(",")
    ori = ori_lat + "," + ori_lng
    des = des_lat + "," + des_lng

    url = "http://api.map.baidu.com/directionlite/v1/walking?origin=" + \
          ori + "&destination=" + des + "&ak=" + Du_AK
    walk_steps = requests.get(url).text  # json
    walk_steps = json.loads(walk_steps)  # dict

    if walk_steps["status"] == 0:
        steps = walk_steps['result']['routes'][0]['steps']

        print("--> start save routes")
        with open(save_file, "w") as f:
            for step in steps:

                # 输出途径的经纬度
                lng_lats = step['path'].split(";")
                for lng_lat in lng_lats:
                    # print(lng_lat)
                    f.write(lng_lat + "\n")
        print("--> save routes over")


def main():
    ori = "41.771871,123.421867"  # 东北大学汉卿会堂
    des = "41.77025,123.425842"  # 东北大学综合楼

    save_route_points(ori, des, "tt.txt")


if __name__ == "__main__":
    main()

"""
123.42160486207,41.771856760044
123.42161115021,41.771794890133
123.42163181124,41.771733692661
123.42166504854,41.771670477628
123.42170098076,41.771623402563
123.42174769265,41.771579017469
123.42179620115,41.771544652626
123.42185818423,41.771511027516
123.42191387917,41.771485539672
123.42197406564,41.771471417115
123.42204593008,41.771459984566
123.42213396402,41.771451242028
123.42310233736,41.771400804283
123.42338799851,41.771382646685
123.42400782931,41.771355074027
123.42498608401,41.771293876132
123.42497799926,41.771203760444
123.42490972804,41.770448464911
123.42503010098,41.770441739774
123.42521515192,41.770453239757
123.42518640614,41.770174146026
123.425212457,41.770119672167
123.42525288075,41.770073268473
123.42533103333,41.770042332658
123.42580893186,41.7700066892
"""
