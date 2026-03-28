"""排期预测工具函数"""
from typing import List

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from config.algorithm_config import SCHEDULE_MODEL_CONFIG

def preprocess_historical_data(raw_data: List[dict]) -> pd.DataFrame:
    """预处理历史维修数据"""
    df = pd.DataFrame(raw_data)
    # 特征工程
    df["worker_id_num"] = df["worker_id"].apply(lambda x: int(x.replace("W", "")))
    df["repair_duration"] = df["repair_duration"].astype(float)
    # 缺失值处理
    df = df.fillna(0)
    # 选择特征列
    X = df[SCHEDULE_MODEL_CONFIG["feature_cols"]]
    y = df["repair_duration"]
    return X, y

def train_schedule_model(raw_data: List[dict], save_path: str = SCHEDULE_MODEL_CONFIG["model_path"]):
    """训练排期预测模型"""
    # 预处理数据
    X, y = preprocess_historical_data(raw_data)
    # 划分训练集
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    # 训练模型
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    # 评估模型
    score = model.score(X_test, y_test)
    print(f"模型训练完成，R²评分: {score:.4f}")
    # 保存模型
    import pickle
    with open(save_path, "wb") as f:
        pickle.dump(model, f)
    return model