"""地理坐标转换工具"""
import math

def bd09_to_wgs84(bd_lat, bd_lng):
    """
    百度坐标系(BD-09)转WGS84坐标系
    :param bd_lat: 百度纬度
    :param bd_lng: 百度经度
    :return: (wgs_lat, wgs_lng)
    """
    x_pi = 3.14159265358979324 * 3000.0 / 180.0
    x = bd_lng - 0.0065
    y = bd_lat - 0.006
    z = math.sqrt(x * x + y * y) - 0.00002 * math.sin(y * x_pi)
    theta = math.atan2(y, x) - 0.000003 * math.cos(x * x_pi)
    wgs_lng = z * math.cos(theta)
    wgs_lat = z * math.sin(theta)
    return (wgs_lat, wgs_lng)

def wgs84_to_bd09(wgs_lat, wgs_lng):
    """WGS84坐标系转百度坐标系(BD-09)"""
    x_pi = 3.14159265358979324 * 3000.0 / 180.0
    x = wgs_lng
    y = wgs_lat
    z = math.sqrt(x * x + y * y) + 0.00002 * math.sin(y * x_pi)
    theta = math.atan2(y, x) + 0.000003 * math.cos(x * x_pi)
    bd_lng = z * math.cos(theta) + 0.0065
    bd_lat = z * math.sin(theta) + 0.006
    return (bd_lat, bd_lng)