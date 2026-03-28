"""阿里云OSS操作工具（类封装版）"""
import os
from typing import Optional, Union
from oss2 import Auth, Bucket, exceptions
from config.data_config import OSS_CONFIG
from common.log_utils import logger


class OssOper:
    """阿里云OSS操作类（统一数据库模块的类风格）"""

    def __init__(self):
        """初始化OSS配置与客户端"""
        self.config = OSS_CONFIG
        self.auth = None
        self.bucket = None
        self._init_client()

    def _init_client(self):
        """初始化OSS客户端（私有方法）"""
        try:
            # 校验配置完整性
            required_config = ["access_key_id", "access_key_secret", "endpoint", "bucket_name"]
            missing = [k for k in required_config if k not in self.config or not self.config[k]]
            if missing:
                logger.error(f"OSS配置缺失: {missing}")
                return

            # 初始化认证与Bucket
            self.auth = Auth(self.config["access_key_id"], self.config["access_key_secret"])
            self.bucket = Bucket(self.auth, self.config["endpoint"], self.config["bucket_name"])
            # 验证连接
            self.bucket.get_bucket_info()
            logger.info("OSS客户端初始化成功")
        except exceptions.OssError as e:
            logger.error(f"OSS客户端初始化失败（OssError）: {e}")
        except Exception as e:
            logger.error(f"OSS客户端初始化失败（未知错误）: {e}")

    def upload_file(
            self,
            local_file: str,
            remote_path: str,
            overwrite: bool = True
    ) -> Optional[str]:
        """
        上传文件到OSS
        :param local_file: 本地文件路径（必须存在且为文件）
        :param remote_path: OSS远程路径（如 "fault_images/2026/03/test.jpg"）
        :param overwrite: 是否覆盖已存在的文件
        :return: OSS文件URL（失败返回None）
        """
        # 前置校验
        if not self.bucket:
            logger.error("OSS客户端未初始化，上传失败")
            return None
        if not os.path.exists(local_file):
            logger.error(f"本地文件不存在: {local_file}")
            return None
        if not os.path.isfile(local_file):
            logger.error(f"不是有效文件: {local_file}")
            return None

        try:
            # 检查文件是否已存在（可选）
            if not overwrite and self.bucket.object_exists(remote_path):
                logger.warning(f"OSS文件已存在，跳过上传: {remote_path}")
                return self.get_file_url(remote_path)

            # 上传文件
            with open(local_file, "rb") as f:
                self.bucket.put_object(remote_path, f)

            # 生成访问URL
            file_url = self.get_file_url(remote_path)
            logger.info(f"文件上传成功: {local_file} -> {file_url}")
            return file_url
        except exceptions.OssError as e:
            logger.error(f"OSS上传失败（OssError）: {e}, 本地文件: {local_file}, 远程路径: {remote_path}")
        except Exception as e:
            logger.error(f"OSS上传失败（未知错误）: {e}, 本地文件: {local_file}")
        return None

    def download_file(
            self,
            oss_url_or_remote_path: str,
            local_dir: str = "temp/oss_files/"
    ) -> Optional[str]:
        """
        从OSS下载文件（兼容URL/远程路径两种输入）
        :param oss_url_or_remote_path: OSS文件URL 或 远程路径
        :param local_dir: 本地保存目录（自动创建）
        :return: 本地文件路径（失败返回None）
        """
        if not self.bucket:
            logger.error("OSS客户端未初始化，下载失败")
            return None

        # 解析远程路径（兼容URL和纯路径）
        if "http" in oss_url_or_remote_path:
            # 从URL解析远程路径
            prefix = f"{self.config['bucket_name']}.{self.config['endpoint']}/"
            if prefix not in oss_url_or_remote_path:
                logger.error(f"无效的OSS URL: {oss_url_or_remote_path}")
                return None
            remote_path = oss_url_or_remote_path.split(prefix)[-1]
        else:
            # 直接使用远程路径
            remote_path = oss_url_or_remote_path

        try:
            # 创建本地目录
            os.makedirs(local_dir, exist_ok=True)
            # 生成本地文件路径
            file_name = os.path.basename(remote_path)
            local_file = os.path.join(local_dir, file_name)

            # 下载文件
            self.bucket.get_object_to_file(remote_path, local_file)

            # 校验下载结果
            if os.path.exists(local_file) and os.path.getsize(local_file) > 0:
                logger.info(f"文件下载成功: {remote_path} -> {local_file}")
                return local_file
            else:
                logger.error(f"下载文件为空或不存在: {local_file}")
                os.remove(local_file) if os.path.exists(local_file) else None
                return None
        except exceptions.OssError as e:
            logger.error(f"OSS下载失败（OssError）: {e}, 远程路径: {remote_path}")
        except Exception as e:
            logger.error(f"OSS下载失败（未知错误）: {e}, 远程路径: {remote_path}")
        return None

    def get_file_url(self, remote_path: str) -> Optional[str]:
        """
        生成OSS文件的公开访问URL
        :param remote_path: OSS远程路径
        :return: 访问URL（失败返回None）
        """
        if not self.bucket:
            logger.error("OSS客户端未初始化，无法生成URL")
            return None
        try:
            # 拼接标准OSS URL
            url = f"https://{self.config['bucket_name']}.{self.config['endpoint']}/{remote_path}"
            return url
        except Exception as e:
            logger.error(f"生成OSS URL失败: {e}, 远程路径: {remote_path}")
            return None

    def delete_file(self, remote_path: str) -> bool:
        """
        删除OSS文件
        :param remote_path: OSS远程路径
        :return: 是否删除成功
        """
        if not self.bucket:
            logger.error("OSS客户端未初始化，删除失败")
            return False
        try:
            if self.bucket.object_exists(remote_path):
                self.bucket.delete_object(remote_path)
                logger.info(f"文件删除成功: {remote_path}")
                return True
            else:
                logger.warning(f"OSS文件不存在，无需删除: {remote_path}")
                return True
        except exceptions.OssError as e:
            logger.error(f"OSS删除失败（OssError）: {e}, 远程路径: {remote_path}")
        except Exception as e:
            logger.error(f"OSS删除失败（未知错误）: {e}, 远程路径: {remote_path}")
        return False

    def check_file_exists(self, remote_path: str) -> bool:
        """
        检查OSS文件是否存在
        :param remote_path: OSS远程路径
        :return: 是否存在
        """
        if not self.bucket:
            logger.error("OSS客户端未初始化，无法检查文件")
            return False
        try:
            return self.bucket.object_exists(remote_path)
        except exceptions.OssError as e:
            logger.error(f"检查OSS文件失败（OssError）: {e}, 远程路径: {remote_path}")
        except Exception as e:
            logger.error(f"检查OSS文件失败（未知错误）: {e}, 远程路径: {remote_path}")
        return False


# 全局实例（与RedisOper/MysqlOper保持一致）
oss_oper = OssOper()


# 兼容原有函数（避免修改历史代码）
def upload_oss_file(local_file: str, remote_path: str) -> str:
    """兼容旧接口：上传文件到OSS"""
    return oss_oper.upload_file(local_file, remote_path) or ""


def download_oss_file(oss_url: str, local_path: str = "temp/") -> str:
    """兼容旧接口：从OSS下载文件"""
    return oss_oper.download_file(oss_url, local_path) or ""