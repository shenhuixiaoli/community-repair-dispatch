from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from passlib.context import CryptContext
import pymysql
import datetime
import re

# 初始化Flask应用
app = Flask(__name__)

# 配置项
app.config['JWT_SECRET_KEY'] = 'your-secret-key-20260323'  # 生产环境请改为随机复杂字符串
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(hours=2)  # token有效期2小时

# 初始化JWT
jwt = JWTManager(app)

# 密码加密配置（使用bcrypt算法）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 数据库连接配置
DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': 'root123456',  # 替换为你的MySQL密码
    'database': 'community_algorithm_service',  # 替换为你的数据库名
}


# 数据库连接工具函数
def get_db_connection():
    """获取数据库连接"""
    conn = pymysql.connect(**DB_CONFIG)
    return conn


# 密码验证函数
def verify_password(plain_password, hashed_password):
    """验证密码是否正确"""
    return pwd_context.verify(plain_password, hashed_password)


# 密码加密函数
def get_password_hash(password):
    """生成密码的哈希值"""
    return pwd_context.hash(password)


# 登录接口
@app.route('/api/user/login', methods=['POST'])
def login():
    """
    用户登录接口
    请求参数：JSON格式
    {
        "username": "admin",
        "password": "123456"
    }
    """
    # 1. 获取并验证请求参数
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'code': 400,
                'msg': '请求参数不能为空',
                'data': None,
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }), 400

        username = data.get('username', '').strip()
        password = data.get('password', '').strip()

        # 参数合法性校验
        if not username:
            return jsonify({
                'code': 400,
                'msg': '用户名不能为空',
                'data': None,
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }), 400

        if not password:
            return jsonify({
                'code': 400,
                'msg': '密码不能为空',
                'data': None,
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }), 400

        # 2. 查询用户信息
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(pymysql.cursors.DictCursor)

            # 查询用户
            sql = """
                SELECT id, username, password, real_name, latitude, longitude, status 
                FROM sys_user 
                WHERE username = %s
            """
            cursor.execute(sql, (username,))
            user = cursor.fetchone()

            # 用户不存在
            if not user:
                return jsonify({
                    'code': 401,
                    'msg': '用户名或密码错误',
                    'data': None,
                    'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }), 401

            # 用户被禁用
            if user['status'] == 0:
                return jsonify({
                    'code': 403,
                    'msg': '账号已被禁用，请联系管理员',
                    'data': None,
                    'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }), 403

            # 3. 验证密码
            if not verify_password(password, user['password']):
                return jsonify({
                    'code': 401,
                    'msg': '用户名或密码错误',
                    'data': None,
                    'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }), 401

            # 4. 更新最后登录信息
            login_ip = request.remote_addr
            update_sql = """
                UPDATE sys_user 
                SET last_login_time = %s, last_login_ip = %s 
                WHERE id = %s
            """
            cursor.execute(update_sql, (
                datetime.datetime.now(),
                login_ip,
                user['id']
            ))
            conn.commit()

            # 5. 生成JWT token
            access_token = create_access_token(
                identity=user['id'],
                additional_claims={
                    'username': user['username'],
                    'real_name': user['real_name']
                }
            )

            # 6. 构造返回数据
            user_info = {
                'user_id': user['id'],
                'username': user['username'],
                'real_name': user['real_name'],
                'latitude': float(user['latitude']) if user['latitude'] else None,
                'longitude': float(user['longitude']) if user['longitude'] else None,
                'token': access_token
            }

            return jsonify({
                'code': 200,
                'msg': '登录成功',
                'data': user_info,
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }), 200

        except Exception as e:
            if conn:
                conn.rollback()
            return jsonify({
                'code': 500,
                'msg': f'服务器内部错误：{str(e)}',
                'data': None,
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }), 500
        finally:
            if conn:
                conn.close()

    except Exception as e:
        return jsonify({
            'code': 400,
            'msg': f'请求参数格式错误：{str(e)}',
            'data': None,
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }), 400


# 测试接口：获取当前登录用户信息（需要token）
@app.route('/api/user/info', methods=['GET'])
@jwt_required()
def get_user_info():
    """获取当前登录用户信息"""
    current_user_id = get_jwt_identity()

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    sql = """
        SELECT id, username, real_name, latitude, longitude, last_login_time 
        FROM sys_user 
        WHERE id = %s
    """
    cursor.execute(sql, (current_user_id,))
    user = cursor.fetchone()

    conn.close()

    return jsonify({
        'code': 200,
        'msg': '查询成功',
        'data': {
            'user_id': user['id'],
            'username': user['username'],
            'real_name': user['real_name'],
            'latitude': float(user['latitude']) if user['latitude'] else None,
            'longitude': float(user['longitude']) if user['longitude'] else None,
            'last_login_time': user['last_login_time'].strftime('%Y-%m-%d %H:%M:%S') if user[
                'last_login_time'] else None
        },
        'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }), 200


# 密码加密工具接口（用于生成测试密码）
@app.route('/api/user/encrypt-pwd', methods=['POST'])
def encrypt_password():
    """密码加密接口（仅用于测试）"""
    data = request.get_json()
    password = data.get('password', '')
    return jsonify({
        'code': 200,
        'msg': '加密成功',
        'data': {'hashed_password': get_password_hash(password)},
        'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }), 200


if __name__ == '__main__':
    # 安装依赖：pip install flask flask-jwt-extended passlib bcrypt pymysql
    app.run(host='0.0.0.0', port=5000, debug=True)