"""故障识别工具函数"""
import cv2
import numpy as np
from PIL import Image
import torch

from database.oss_oper import download_oss_file


def preprocess_image(img_source, input_size=(224, 224)):
    """
    图像预处理
    :param img_source: 本地路径/OSS URL
    :param input_size: 模型输入尺寸
    :return: 预处理后的图像张量
    """
    # 1. 加载图片
    if img_source.startswith("http") or "oss" in img_source:
        # OSS图片下载
        img_path = download_oss_file(img_source)
    else:
        img_path = img_source

    # 2. 预处理
    img = cv2.imread(img_path)
    img = cv2.resize(img, input_size)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = np.transpose(img, (2, 0, 1)) / 255.0
    img = torch.from_numpy(img).float().unsqueeze(0)  # 需import torch
    return img


def parse_fault_label(label_str):
    """
    解析故障标签（y_故障类型_严重程度_紧急程度）
    :param label_str: 标签字符串
    :return: 解析后的字典
    """
    try:
        if not label_str.startswith("y_"):
            raise ValueError("标签格式错误")
        parts = label_str.split("_")[1:]
        return {
            "fault_type": int(parts[0]),
            "severity": int(parts[1]),
            "urgency": int(parts[2])
        }
    except Exception as e:
        print(f"解析故障标签失败: {e}")
        return {"fault_type": -1, "severity": -1, "urgency": -1}