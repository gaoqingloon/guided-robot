# -*- coding:UTF-8 -*-

"""
    如何在行进中添加语音
    比如：
        “前方xxx米有障碍物”
        “向左/右转向”
        “当前朝向为” + str(compass.heading())

    # xxx米：超声波测距模块
    # 遇到障碍物躲避：红外避障模块
"""

import RPi.GPIO as GPIO
import time
import ctypes
import inspect

# 小车电机引脚定义
ENA = 16
ENB = 13

# 小车按键定义
key = 8

# 超声波引脚定义
EchoPin = 0
TrigPin = 1

# 红外避障引脚定义
AvoidSensorLeft = 12
AvoidSensorRight = 17

#设置GPIO口为BCM编码方式
GPIO.setmode(GPIO.BCM)

#忽略警告信息
GPIO.setwarnings(False)


class Avoid(object):
    """ 避障程序 """

    def init(self):
        """ 引脚初始化 """
        global pwm_ENA
        global pwm_ENB

        GPIO.setup(ENA, GPIO.OUT, initial=GPIO.HIGH)
        GPIO.setup(ENB, GPIO.OUT, initial=GPIO.HIGH)

        GPIO.setup(key, GPIO.IN)
        GPIO.setup(EchoPin, GPIO.IN)
        GPIO.setup(TrigPin, GPIO.OUT)

        GPIO.setup(AvoidSensorLeft, GPIO.IN)
        GPIO.setup(AvoidSensorRight, GPIO.IN)

        # 设置pwm引脚和频率为2000hz
        pwm_ENA = GPIO.PWM(ENA, 2000)
        pwm_ENB = GPIO.PWM(ENB, 2000)
        pwm_ENA.start(0)
        pwm_ENB.start(0)

    def ultrasonic_avoid(self):
        time.sleep(2)
        try:
            # self.init()
            # self.key_scan()

            distance = self.distance_test()
            msg = None
            # 距离小于半米，语音提示
            if distance < 80:
                distance /= 100
                # 报出“前方xxx米有障碍物”
                msg = "前方" + str(round(distance, 1)) + "米处有障碍物"
            return msg
        except Exception:
            pass

    def infrared_avoid(self):
        time.sleep(2)
        try:
            # self.init()
            # self.key_scan()

            # 遇到障碍物,红外避障模块的指示灯亮,端口电平为LOW
            # 未遇到障碍物,红外避障模块的指示灯灭,端口电平为HIGH
            left_sensor_value = GPIO.input(AvoidSensorLeft)
            right_sensor_value = GPIO.input(AvoidSensorRight)

            # 右边探测到有障碍物，有信号返回，原地向左转
            msg = None
            if left_sensor_value == True and right_sensor_value == False:
                # 测出当前距离障碍物的距离
                distance = self.distance_test()
                distance /= 100
                # 报出“前方xxx米有障碍物”
                msg = "右侧前方" + str(round(distance, 1)) + "米处有障碍物，请向左转"

            # 左边探测到有障碍物，有信号返回，原地向右转
            elif right_sensor_value == True and left_sensor_value == False:
                # 测出当前距离障碍物的距离
                distance = self.distance_test()
                distance /= 100
                # 报出“前方xxx米有障碍物”
                msg = "左侧前方" + str(round(distance, 1)) + "米处有障碍物，请向右转"

            # 当两侧均检测到障碍物时调用固定方向的避障(原地右转)
            elif right_sensor_value == False and left_sensor_value == False:
                # 测出当前距离障碍物的距离
                distance = self.distance_test()
                distance /= 100
                # 报出“前方xxx米有障碍物”
                msg = "正前方" + str(round(distance, 1)) + "米处有障碍物"
            return msg
        except Exception:
            pass

    def key_scan(self):
        """ 按键检测 """
        while GPIO.input(key):
            pass
        while not GPIO.input(key):
            time.sleep(0.01)
            if not GPIO.input(key):
                time.sleep(0.01)
                while not GPIO.input(key):
                    pass

    def distance(self):
        """ 超声波函数 """
        # 发出触发信号
        GPIO.output(TrigPin, GPIO.HIGH)
        # 保持15us的超声波发射，避免能量太低无法返回
        time.sleep(0.000015)
        # 置位管脚低电平，停止发射超声波
        GPIO.output(TrigPin, GPIO.LOW)
        while not GPIO.input(EchoPin):
            pass
        # 发现高电平时开时计时
        t1 = time.time()
        # 如果有检测到反射返回的超声波，那么就持续计时，否则就跳出循环，计时结束
        while GPIO.input(EchoPin):
            pass
        # 高电平结束停止计时
        t2 = time.time()
        print("per test distance(cm):", ((t2 - t1) * 340.0 / 2) * 100)
        time.sleep(0.01)
        # 返回距离，单位为cm(cm = M * 100)
        return ((t2 - t1) * 340.0 / 2) * 100

    def distance_test(self):
        """ 
            超声波测5次，去掉最大值和最小值，取平局值，提高测试准确性
            范围: 3-450cm, 0.03-4.5m
        """
        # self.init()
        dis_list = []
        for i in range(5):
            dis = self.distance()
            # 过滤掉测试中出现问题的数据 (3-450cm)
            while (dis >= 500) or (dis <= 0):
                dis = self.distance()
            dis_list.append(dis)
        dis_list.sort()
        return (dis_list[1] + dis_list[2] + dis_list[3]) / 3


    def close(self):
        """ 复位引脚 """
        pwm_ENA.stop()
        pwm_ENB.stop()
        GPIO.cleanup()


def _async_raise(tid, exctype):
    """raises the exception, performs cleanup if needed"""
    tid = ctypes.c_long(tid)
    if not inspect.isclass(exctype):
        exctype = type(exctype)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
    if res == 0:
        raise ValueError("invalid thread id")
    elif res != 1:
        # """if it returns a number greater than one, you're in trouble,
        # and you should call it again with exc=NULL to revert the effect"""
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
        raise SystemError("PyThreadState_SetAsyncExc failed")


def stop_thread(thread):
    _async_raise(thread.ident, SystemExit)


def main():
    robot = Avoid()
    robot.init()
    
    # 2. 超声波避障测试
    for i in range(10):
        print(robot.ultrasonic_avoid())
        time.sleep(1)

    # 3. 红外避障测试
    for i in range(10):
        print(robot.infrared_avoid())
        time.sleep(1)


if __name__ == '__main__':
    main()
