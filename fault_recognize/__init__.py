# 故障识别模块初始化
from .predict import predict_fault
from .utils import preprocess_image, parse_fault_label

__all__ = ["predict_fault", "preprocess_image", "parse_fault_label"]