"""故障等级与类型识别核心函数（集成两级模型）"""
import os
import torch
from torchvision import transforms

from config.algorithm_config import FAULT_MODEL_CONFIG
from fault_recognize.utils import preprocess_image
from fault_recognize.model_def import (
    DEVICE,
    build_stage1_model_structure,
    FaultDegreeModel,
    FAULT_TYPE_CLASSES,
    TYPE_ID_TO_NAME,
    FAULT_TYPE_TO_CODE,
    SEVERITY_ID_TO_NAME,
    URGENCY_ID_TO_NAME,
)

# ====== 构建 & 加载模型 ======
def _load_stage1_model():
    model = build_stage1_model_structure().to(DEVICE)
    ckpt_path = FAULT_MODEL_CONFIG["stage1_model_path"]
    if not os.path.exists(ckpt_path):
        raise FileNotFoundError(f"Stage1 模型不存在: {ckpt_path}")
    ckpt = torch.load(ckpt_path, map_location=DEVICE)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    return model


def _load_stage2_model():
    model = FaultDegreeModel().to(DEVICE)
    ckpt_path = FAULT_MODEL_CONFIG["stage2_model_path"]
    if not os.path.exists(ckpt_path):
        raise FileNotFoundError(f"Stage2 模型不存在: {ckpt_path}")
    ckpt = torch.load(ckpt_path, map_location=DEVICE)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    return model


# 图像标准化（和训练时保持一致）
_normalize = transforms.Normalize(
    mean=[0.485, 0.456, 0.406],
    std=[0.229, 0.224, 0.225]
)

# 全局只加载一次，避免每次请求都重新建模
try:
    stage1_model = _load_stage1_model()
    stage2_model = _load_stage2_model()
except Exception as e:
    print(f"加载故障识别模型失败: {e}")
    stage1_model = None
    stage2_model = None


def predict_fault(img_source):
    """
    故障识别核心函数（两级模型）
    :param img_source: 图片本地路径/阿里云OSS URL
    :return: 结构化故障识别结果
    """
    # 如果模型没加载成功，直接返回错误
    if stage1_model is None or stage2_model is None:
        return {
            "fault_label": "",
            "fault_type": -1,
            "severity": -1,
            "urgency": -1,
            "confidence": 0.0,
            "img_url": img_source,
            "is_valid": False,
            "error": "fault models not loaded"
        }

    try:
        # 1. 图像预处理（大小+归一化到[0,1]，转 tensor）
        img = preprocess_image(img_source, FAULT_MODEL_CONFIG["input_size"])
        img = _normalize(img.squeeze(0)).unsqueeze(0).to(DEVICE)   # 加标准化

        with torch.no_grad():
            # ===== 第一级：是否有故障 + 故障大类 =====
            logits1 = stage1_model(img)
            prob1 = torch.softmax(logits1, dim=1)
            conf1, pred1 = prob1.max(dim=1)

            type_id = int(pred1.item())
            type_conf = float(conf1.item())

            # “无故障” 直接返回
            if TYPE_ID_TO_NAME.get(type_id, "") == "无故障":
                result = {
                    "fault_label": "n_-1_-1_-1",
                    "fault_type": -1,
                    "severity": -1,
                    "urgency": -1,
                    "confidence": type_conf,
                    "img_url": img_source,
                    "is_valid": type_conf >= FAULT_MODEL_CONFIG["confidence_threshold"]
                }
                return result

            fault_type_name = TYPE_ID_TO_NAME[type_id]          # 如 “水管漏水”
            fault_type_code = FAULT_TYPE_TO_CODE[fault_type_name]  # 业务内部使用的 0~6 编码

            # ===== 第二级：严重程度 + 紧急程度 =====
            fault_code_tensor = torch.tensor([fault_type_code], dtype=torch.long, device=DEVICE)
            sev_logits, urg_logits = stage2_model(img, fault_code_tensor)

            sev_prob = torch.softmax(sev_logits, dim=1)
            urg_prob = torch.softmax(urg_logits, dim=1)

            sev_conf, sev_pred = sev_prob.max(dim=1)
            urg_conf, urg_pred = urg_prob.max(dim=1)

            severity = int(sev_pred.item())
            urgency = int(urg_pred.item())

            # 综合置信度，可以按需要定义，这里取三者最小值
            confidence = float(min(type_conf, sev_conf.item(), urg_conf.item()))

        fault_label = f"y_{fault_type_code}_{severity}_{urgency}"

        result = {
            "fault_label": fault_label,
            "fault_type": fault_type_code,   # 和 DISPATCH / SCHEDULE 用的编码一致
            "severity": severity,
            "urgency": urgency,
            "confidence": confidence,
            "img_url": img_source,
            "is_valid": confidence >= FAULT_MODEL_CONFIG["confidence_threshold"],
            "fault_type_name": fault_type_name,
            "severity_name": SEVERITY_ID_TO_NAME.get(severity, ""),
            "urgency_name": URGENCY_ID_TO_NAME.get(urgency, "")
        }
        return result

    except Exception as e:
        print(f"故障识别失败: {e}")
        return {
            "fault_label": "",
            "fault_type": -1,
            "severity": -1,
            "urgency": -1,
            "confidence": 0.0,
            "img_url": img_source,
            "is_valid": False,
            "error": str(e)
        }