# import serial
import pynmea2
import json
import requests
"""
serial: 串口库
pynmea2: 解析NMEA语句的库
"""
# Du config
Du_AK = "zspWrePa3M6jwZYDfXFWnKp6rHBSwXj7"


def get_cur_loc_by_gps(serial_port):
    """ 通过GPS模块获取经纬度信息，并进行解析 "lat,lon" """
    # return "123.421867,41.771871"
    # 配置使用usb连接串口
    # serial_port = serial.Serial("/dev/ttyUSB0", 9600, timeout=0.5)

    while True:
        data = serial_port.readline()  # <class 'bytes'>

        if data.find('GGA') > 0:
            try:
                data = str(data, encoding = "utf8")
                msg = pynmea2.parse(data)
                print("Timestamp: %s -- Lat: %s %s -- Lon: %s %s -- Altitude: %s %s" % (
                    msg.timestamp, msg.lat, msg.lat_dir, msg.lon, msg.lon_dir, msg.altitude, msg.altitude_units))
                if msg.lon and msg.lat:
                    lon = parse(msg.lon)
                    lat = parse(msg.lat)
                    print("parse:", str(lon) + "," + str(lat))
                    # 返回 "纬度,经度" 信息
                    return str(lon) + "," + str(lat)
            except:
                pass


def parse(ori_deg):
    """
    【度分秒 => 度】
    """
    ori_deg = float(ori_deg)
    du = int(ori_deg / 100)
    fen = int((ori_deg/100 - du)*100)
    miao = ((ori_deg/100 - du)*100 - fen) * 60
    return round(du + fen/60 + miao/3600, 6)


def convert(ori_lon_lat):
    """ request map url for convert
    由gps模块得到的(经度,纬度)，转为百度地图的(经度,纬度)
    """
    url = "http://api.map.baidu.com/geoconv/v1/?coords=" + ori_lon_lat + \
          "&from=1&to=5&ak=" + Du_AK
    res_json = requests.get(url).text  # json
    res_dict = json.loads(res_json)  # dict

    if res_dict["status"] == 0:
        lng = str(round(res_dict["result"][0]["x"], 6))
        lat = str(round(res_dict["result"][0]["y"], 6))
        return lng + "," + lat  # 纬度,经度
    else:
        return ori_lon_lat


def main():
    serial_port = serial.Serial("/dev/ttyUSB0", 9600, timeout=0.5)
    while True:
        print(get_cur_loc_by_gps(serial_port))


if __name__ == '__main__':
    main()
