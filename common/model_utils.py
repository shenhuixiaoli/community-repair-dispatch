"""模型加载公共函数"""
import torch

def load_pytorch_model(model_path: str, device: str = "cpu") -> torch.nn.Module:
    """
    加载PyTorch模型
    :param model_path: 模型文件路径
    :param device: 设备（cpu/cuda）
    :return: 加载的模型
    """
    try:
        model = torch.load(model_path, map_location=device)
        model.eval()
        return model
    except Exception as e:
        print(f"加载PyTorch模型失败: {e}")
        return None

def load_sklearn_model(model_path: str):
    """加载Scikit-learn模型"""
    import pickle
    try:
        with open(model_path, "rb") as f:
            model = pickle.load(f)
        return model
    except Exception as e:
        print(f"加载Scikit-learn模型失败: {e}")
        return None