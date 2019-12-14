import math
import os

# cur_path = os.path.dirname(__file__)


class ETLUtil(object):
    """ 提取转弯点并写入文件 """

    def __init__(self, ori_file, des_file, threshold=30.0):
        self.ori_file = ori_file
        self.des_file = des_file
        self.threshold = threshold  # 阈值设置为30°（当前角度与后面某个角度大于30°提取为转弯点）

    @staticmethod
    def calc_angle(x1, y1, x2, y2):
        """ 返回角度 """
        denominator = float(x2) - float(x1)
        if denominator == 0:
            denominator = 0.0000001
        return math.atan((float(y2) - float(y1)) / denominator) * 180.0 / math.pi

    def compute_and_save(self):
        """
            1、读取原始文件
            2、提取转弯点(阈值设为30°)
            3、提取后的转弯点写入文件
        """
        # 1、读取原始文件
        x_y_list = []
        # with open(os.path.join(cur_path, self.ori_file)) as f:
        with open(self.ori_file) as f:
            for line in f:
                lon = line.split(",")[0]
                lat = line.split(",")[1].replace("\n", "")
                x_y_list.append((lon, lat))
        # print("x_y_list)

        # 2、进行处理，提取转弯点
        angle_list = []
        for i in range(0, len(x_y_list) - 1):
            for j in range(i + 1, len(x_y_list)):
                if j - i >= 2:
                    break
                angle = self.calc_angle(x_y_list[i][0], x_y_list[i][1],
                                        x_y_list[j][0], x_y_list[j][1])
                angle_list.append((angle, (x_y_list[i][0], x_y_list[i][1])))
        # print(angle_list)
        # print(len(angle_list))

        # ori:25 angle:24 abs=23
        abs_list = []
        index = -1
        for i in range(0, len(angle_list) - 1):
            if index <= i:
                for j in range(i + 1, len(angle_list)):
                    # print("i: ", i)
                    # print("j: ", j)
                    abs_value = math.fabs(angle_list[i][0] - angle_list[j][0])
                    if abs_value >= self.threshold:
                        abs_list.append((abs_value, angle_list[j][1]))
                        index = j
                        break

        # 3、将转弯点写入文件
        with open(self.des_file, "w") as f:
            f.write(x_y_list[0][0] + "," + x_y_list[0][1] + "\n")  # 起始点
            for item in abs_list:
                f.write(str(item[1][0]) + "," + str(item[1][1]) + "\n")  # 转弯点
            f.write(x_y_list[-1][0] + "," + x_y_list[-1][1] + "\n")  # 终止点


def main():
    etl = ETLUtil(ori_file="record_point.txt", des_file="turn.txt", threshold=30.0)
    etl.compute_and_save()
    print("over")


if __name__ == '__main__':
    main()
