import math


def cal_distance(ori_lng_lat, des_lng_lat):
    """
        计算经纬度之间的距离，单位为米
         (lng,lat),(lng,lat) -> distance
    """
    earth_radius = 6378137
    ori_lng = ori_lng_lat.split(",")[0]
    ori_lat = ori_lng_lat.split(",")[1]
    des_lng = des_lng_lat.split(",")[0]
    des_lat = des_lng_lat.split(",")[1]
    rad_lat1 = float(ori_lat) * math.pi / 180.0
    rad_lat2 = float(des_lat) * math.pi / 180.0
    rad_lng1 = float(ori_lng) * math.pi / 180.0
    rad_lng2 = float(des_lng) * math.pi / 180.0

    a = rad_lat1 - rad_lat2
    b = rad_lng1 - rad_lng2
    dis = 2 * math.asin(
        math.sqrt(math.pow(math.sin(a / 2), 2) +
                  math.cos(rad_lat1) * math.cos(rad_lat2) * math.pow(math.sin(b / 2), 2)))
    dis *= earth_radius
    return dis


def main():
    # origin xy
    ORI = "123.42160486207,41.771856760044"
    DES = "123.42166504854,41.771670477628"
    print(cal_distance(ORI, DES))

    ORI_ = "123.421604,41.771856"
    DES_ = "123.421665,41.771670"
    print(cal_distance(ORI_, DES_))


if __name__ == '__main__':
    main()
