# fault_recognize/model_def.py
import torch
import torch.nn as nn
from torchvision import models

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ====== 第一级：故障类型（含无故障） ======
FAULT_TYPE_CLASSES = {
    '无故障': 0,
    '楼道灯损坏': 1,
    '桌椅损坏': 2,
    '健身器材损坏': 3,
    '消防栓损坏': 4,
    '水管漏水': 5,
    '地砖翘起': 6,
    '墙面渗水': 7
}
TYPE_ID_TO_NAME = {v: k for k, v in FAULT_TYPE_CLASSES.items()}
FAULT_TYPE_TO_CODE = {
    '楼道灯损坏': 0, '桌椅损坏': 1, '健身器材损坏': 2,
    '消防栓损坏': 3, '水管漏水': 4, '地砖翘起': 5, '墙面渗水': 6
}

SEVERITY_ID_TO_NAME = {0: '轻微', 1: '中度', 2: '严重'}
URGENCY_ID_TO_NAME = {0: '低紧急', 1: '中紧急', 2: '高紧急'}

FAULT_TYPE_NUM = 7      # 0~6 对应 7 种“有故障”类型
EMBEDDING_DIM = 16


def build_stage1_model_structure():
    """和训练第一级时保持一致的结构"""
    model = models.mobilenet_v2(weights=None)
    model.classifier = nn.Sequential(
        nn.Dropout(0.5),
        nn.Linear(model.last_channel, 512),
        nn.ReLU(),
        nn.Dropout(0.3),
        nn.Linear(512, len(FAULT_TYPE_CLASSES))  # 8 类（含无故障）
    )
    return model


class FaultDegreeModel(nn.Module):
    """第二级模型结构（严重程度 + 紧急程度）"""

    def __init__(self, fault_type_num=FAULT_TYPE_NUM, embedding_dim=EMBEDDING_DIM):
        super(FaultDegreeModel, self).__init__()

        self.backbone = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.IMAGENET1K_V1)
        for param in self.backbone.features.parameters():
            param.requires_grad = False
        for param in list(self.backbone.features.parameters())[-10:]:
            param.requires_grad = True
        img_feature_dim = self.backbone.last_channel

        self.fault_type_embedding = nn.Embedding(fault_type_num, embedding_dim)

        self.fusion = nn.Sequential(
            nn.Linear(img_feature_dim + embedding_dim, 256),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.3)
        )

        self.severity_head = nn.Linear(128, 3)  # 严重程度 0/1/2
        self.urgency_head = nn.Linear(128, 3)   # 紧急程度 0/1/2

    def forward(self, img, fault_type_code):
        img_features = self.backbone.features(img)
        img_features = nn.functional.adaptive_avg_pool2d(img_features, 1).reshape(img_features.shape[0], -1)
        fault_embedding = self.fault_type_embedding(fault_type_code)
        fused_features = torch.cat([img_features, fault_embedding], dim=1)
        fused_features = self.fusion(fused_features)
        severity_logits = self.severity_head(fused_features)
        urgency_logits = self.urgency_head(fused_features)
        return severity_logits, urgency_logits