"""MySQL操作工具"""
import pymysql
from typing import List, Dict, Any
from config.data_config import MYSQL_CONFIG
from common.log_utils import logger

class MysqlOper:
    """MySQL操作类"""
    def __init__(self):
        self.config = MYSQL_CONFIG
        self.conn = None
        self.cursor = None

    def connect(self):
        """建立数据库连接"""
        try:
            self.conn = pymysql.connect(**self.config)
            self.cursor = self.conn.cursor(pymysql.cursors.DictCursor)
            return True
        except Exception as e:
            logger.error(f"MySQL连接失败: {e}")
            return False

    def close(self):
        """关闭数据库连接"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

    def query(self, sql: str, params: tuple = None) -> List[Dict[str, Any]]:
        """
        执行查询
        :param sql: 查询SQL
        :param params: 参数元组
        :return: 查询结果列表
        """
        try:
            if not self.connect():
                return []
            self.cursor.execute(sql, params or ())
            result = self.cursor.fetchall()
            self.close()
            return result
        except Exception as e:
            logger.error(f"MySQL查询失败: {e}, SQL: {sql}")
            self.close()
            return []

    def execute(self, sql: str, params: tuple = None) -> bool:
        """
        执行增删改
        :param sql: 执行SQL
        :param params: 参数元组
        :return: 是否成功
        """
        try:
            if not self.connect():
                return False
            self.cursor.execute(sql, params or ())
            self.conn.commit()
            self.close()
            return True
        except Exception as e:
            logger.error(f"MySQL执行失败: {e}, SQL: {sql}")
            self.conn.rollback()
            self.close()
            return False

# 全局实例
mysql_oper = MysqlOper()

def get_historical_repair_data(limit: int = 1000) -> List[Dict[str, Any]]:
    """获取历史维修数据"""
    sql = "SELECT * FROM repair_record LIMIT %s"
    return mysql_oper.query(sql, (limit,))

def save_dispatch_result(result: Dict[str, Any]) -> bool:
    """保存派单结果到数据库"""
    sql = """
    INSERT INTO dispatch_record (order_id, worker_id, fault_type, severity, urgency, 
    comprehensive_score, is_feasible, create_time)
    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
    """
    params = (
        result["order_id"],
        result["dispatch_result"].get("worker_id", ""),
        result["fault_info"]["fault_type"],
        result["fault_info"]["severity"],
        result["fault_info"]["urgency"],
        result["dispatch_result"].get("comprehensive_score", 0.0),
        result["dispatch_result"].get("is_feasible", False)
    )
    return mysql_oper.execute(sql, params)