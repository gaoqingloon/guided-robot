import os
import math
import time

from queue import Queue

cur_path = os.path.dirname(__file__)


class Node(object):
    """
        123.42160486207,41.771856760044
        (经度，纬度)
    """

    def __init__(self, ang, lng, lat):
        self.ang = ang
        self.lng = lng
        self.lat = lat


class Logic(object):
    def __init__(self, turn_file):
        self.turn_file = turn_file
        self.queue = Queue()  # 存储转弯点Node

    @staticmethod
    def get_distance(node1, node2):
        """
            计算经纬度之间的距离，单位为米
             (lng,lat),(lng,lat) -> distance
        """
        earth_radius = 6378137
        rad_lat1 = float(node1.lat) * math.pi / 180.0
        rad_lat2 = float(node2.lat) * math.pi / 180.0
        rad_lng1 = float(node1.lng) * math.pi / 180.0
        rad_lng2 = float(node2.lng) * math.pi / 180.0

        a = rad_lat1 - rad_lat2
        b = rad_lng1 - rad_lng2
        dis = 2 * math.asin(
            math.sqrt(math.pow(math.sin(a / 2), 2) +
                      math.cos(rad_lat1) * math.cos(rad_lat2) * math.pow(math.sin(b / 2), 2)))
        dis *= earth_radius
        return dis

    @staticmethod
    def calc_util(x1, y1, x2, y2):
        """ 角度 """
        denominator = float(x2) - float(x1)
        if denominator == 0:
            denominator = 0.0000001
        return math.atan((float(y2) - float(y1)) / denominator) * 180.0 / math.pi

    def calc_angle(self, x_y_list):
        """ 计算转弯点之间的角度（弧度）"""
        angle_list = []
        for i in range(0, len(x_y_list) - 1):
            for j in range(i + 1, len(x_y_list)):
                if j - i >= 2:
                    break
                angle = self.calc_util(x_y_list[i][0], x_y_list[i][1],
                                       x_y_list[j][0], x_y_list[j][1])
                angle_list.append((angle, (x_y_list[j][0], x_y_list[j][1])))
        return angle_list

    def file_to_queue(self):
        """
        读取转弯点文件，转弯点封装为Node，存入queue
        """
        x_y_list = []
        with open(self.turn_file) as f:
            for line in f:
                lng = line.split(",")[0]
                lat = line.split(",")[1].replace("\n", "")
                x_y_list.append((lng, lat))

        angle_list = self.calc_angle(x_y_list)

        self.queue.put(Node(angle_list[0][0], x_y_list[0][0], x_y_list[0][1]))  # 起始点放入队列（不用放起始点？）
        for node in angle_list:
            self.queue.put(Node(node[0], node[1][0], node[1][1]))  # 转弯点和终止点放入队列

    def test(self):
        """ for test """
        self.file_to_queue()
        while not self.queue.empty():
            print(self.queue.qsize(), end="\t")
            node = self.queue.get()
            print(node.ang, node.lng, node.lat)

    def logic_with_cps(self, cal_node, compass):
        print("cal_angle:", cal_node.ang)
        print("compass:", compass)

        # 设置阈值15度
        if compass - cal_node.ang > 15.0:
            self.right()
        elif compass - cal_node.ang < -15.0:
            self.left()
        else:
            self.head()

    def run_with_cps(self, cal_node, gps, compass):
        """
            起点到终点分为多段路，一段路从queue中读取一个转弯点，15s 读取一次compass
            一个转弯点执行一次run方法
            compass 传入多次
            queue 值获取一次
        """

        loc_node = Node(0, gps.split(",")[0], gps.split(",")[1])

        # 退出逻辑：当前定位与下一个转弯点距离小于5米，
        if self.get_distance(loc_node, cal_node) < 5:
            if self.queue.qsize() == 0:
                print("到达目的地")
            else:
                print("该转弯了")
            return

            # 行走逻辑：当前位置与下一个转弯点夹角 和 电子罗盘角度 关系
        self.logic_with_cps(cal_node=cal_node, compass=compass)

    def left(self):
        return "请将方向向左调整"

    def right(self):
        return "请将方向向右调整"

    def head(self):
        return "请直行"

    def turn_logic(self, cur_node, next_node):
        print("cur_node:", cur_node.ang)
        print("next_node:", next_node.ang)

        # 提示向左/向右转
        if next_node.ang - cur_node.ang > 0:
            return self.right()
        elif next_node.ang - cur_node.ang < 0:
            return self.left()
        else:
            return self.head()

    def walk_logic(self, loc_node, next_node):
        print("loc_node:", loc_node.ang)
        print("next_node:", next_node.ang)

        # 设置阈值15度
        if next_node.ang - loc_node.ang > 15.0:
            msg = self.right()
        elif next_node.ang - loc_node.ang < -15.0:
            msg = self.left()
        else:
            msg = self.head()
        return msg

    def run(self, cal_node_cur, cal_node_next, gps):
        """
            起点到终点分为多段路，一段路从queue中读取一个转弯点
            Node 中封装的是，当前节点和前面的角
        """
        gps_lng = gps.split(",")[0]
        gps_lat = gps.split(",")[1].replace("\n", "")
        gps_ang = self.calc_util(gps_lng, gps_lat, cal_node_next.lng, cal_node_next.lat)
        loc_node = Node(gps_ang, gps_lng, gps_lat)

        # 退出逻辑：当前定位与下一个转弯点距离小于5米，
        print("距离下一点距离为" + str(round(self.get_distance(loc_node, cal_node_next), 1)) + "米")
        # print(self.queue.qsize())
        if self.get_distance(loc_node, cal_node_next) < 3:
            if self.queue.qsize() == 0:
                print("到达目的地")
            else:
                print("到达转弯点，请注意转弯")
                self.turn_logic(cur_node=cal_node_cur, next_node=cal_node_next)
            return

        # 行走逻辑：当前位置 和 下一个转弯点 关系
        self.walk_logic(loc_node=loc_node, next_node=cal_node_next)


def main():
    # # for test
    # 外界模块获取值
    # compass = 30
    # cur_gps = "123.42161115021,41.771794890133"
    # des = "41.77025,123.425842"

    # gps = GPS()
    # cps = Compass()

    # # turn.txt 的获取
    # cur_gps = "41.771871,123.421867"  # 东北大学汉卿会堂
    # # cur_gps = gps.convert()
    # des = "41.77025,123.425842"  # 东北大学综合楼
    # # des = Destination().search("东北大学综合楼")
    #
    # Walk().save_route_points(ori=cur_gps, des=des, save_file="record_test.txt")
    # time.sleep(0.5)
    # ETLUtil(ori_file="record_test.txt", des_file="turn_test.txt", threshold=30.0).compute()
    # print("store turn points to file. over")

    # # 转弯点放入队列(Node的第一个角度是通过后来计算的，Node只是临时的)
    # # 需要把所有的点放入到一个文件中 record.txt，只有经纬度
    # # 通过 dijkstra算法 找到最短路径 即 保存到 turn.txt
    # lc = Logic(turn_file="turn.txt")
    # lc.test()

    lc = Logic(turn_file="turn.txt")
    lc.file_to_queue()  # 转弯点放入队列

    lc_aux = Logic(turn_file="turn.txt")
    lc_aux.file_to_queue()  # 转弯点放入队列
    lc_aux.queue.get()  # 丢掉起始点

    while not lc_aux.queue.empty():
        cal_node_cur = lc.queue.get()  # 起始点
        cal_node_next = lc_aux.queue.get()  # 后一个
        while True:
            with open("test_route.txt") as f:
                for cur_gps in f:
                    lc_aux.run(cal_node_cur=cal_node_cur, cal_node_next=cal_node_next, gps=cur_gps)
            break

    # while not lc_aux.queue.empty():
    #     cal_node_cur = lc.queue.get()  # 起始点
    #     cal_node_next = lc_aux.queue.get()  # 后一个
    #
    #     # 不断通过gps模块获取当前坐标
    #     while True:
    #         cur_gps = gps.convert()
    #         # 封装loc_node
    #         gps_lng = cur_gps.split(",")[0]
    #         gps_lat = cur_gps.split(",")[1].replace("\n", "")
    #         gps_ang = cur_gps.calc_util(gps_lng, gps_lat, cal_node_next.lng, cal_node_next.lat)
    #         loc_node = Node(gps_ang, gps_lng, gps_lat)
    #
    #         # 判停条件
    #         if lc_aux.get_distance(loc_node, cal_node_next) < 3:
    #             if lc_aux.queue.qsize() == 0:
    #                 print("到达目的地")
    #             else:
    #                 print("到达转弯点，请注意转弯")
    #                 lc_aux.turn_logic(cur_node=cal_node_cur, next_node=cal_node_next)
    #             break
    #
    #         # 执行
    #         lc_aux.run(cal_node_cur=cal_node_cur, cal_node_next=cal_node_next, gps=cur_gps)

    print("本次导航结束，谢谢使用")


if __name__ == '__main__':
    main()

# print(Logic.calc_util(0, 0, 1, 1))
# node1 = Node(0, 123.42160486207, 41.771856760044)
# node2 = Node(0, 123.42166504854, 41.771670477628)
# print(Logic.get_distance(node1, node2))
# node3 = Node(0, 123.421867, 41.771872)
# node4 = Node(0, 123.422146, 41.771126)
# print(Logic.get_distance(node3, node4))
