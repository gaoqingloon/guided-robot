"""
    地点输入提示服务
    "东北大学汉卿会堂" -> 41.771864,123.421874 (纬度，经度)
"""
import json
import requests


# Du config
Du_AK = "zspWrePa3M6jwZYDfXFWnKp6rHBSwXj7"


def search(query, region="沈阳"):
    """ 
    query：待查询的地点名称
    region：待查询的城市，默认沈阳
    """
    
    url = "http://api.map.baidu.com/place/v2/suggestion?query=" + \
          query + "&region=" + region + "&city_limit=true&output=json&ak=" + Du_AK

    res_json = requests.get(url).text
    res_dict = json.loads(res_json)

    if res_dict["status"] == 0:
        #print(len(res_dict["result"]))
        first = res_dict["result"][0]
        #print(first["name"])
        return str(first["location"]["lng"]) + "," + str(first["location"]["lat"])
    else:
        return


def main():
    print(search("东北大学汉卿会堂"))
    print(search("东北大学综合楼"))
    print(search("东北大学学生活动中心"))


if __name__ == '__main__':
    main()
