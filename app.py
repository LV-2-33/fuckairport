import requests
from flask import Flask, Response, request, jsonify
import logging
import os
import time

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# 全局变量存储Authorization和最后更新时间
global_token = None
last_token_update = 0
TOKEN_EXPIRY = 3600000  # 假设token有效期为1小时（3600秒）

# 原始API请求的固定头部（User-Agent保持不变）
api_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0"
}

def get_env_or_file(var_name):
    """从环境变量或文件获取值"""
    # 首先检查环境变量
    value = os.getenv(var_name)
    if value:
        return value
    
    # 检查是否有对应的文件环境变量
    file_var = os.getenv(f"{var_name}_FILE")
    if file_var and os.path.exists(file_var):
        try:
            with open(file_var, 'r') as f:
                return f.read().strip()
        except Exception as e:
            app.logger.error(f"读取文件 {file_var} 失败: {str(e)}")
            return None
    
    return None

def get_api_base_url():
    """获取API基础URL，必须设置"""
    base_url = get_env_or_file("API_BASE_URL")
    if not base_url:
        app.logger.error("API_BASE_URL 环境变量未设置")
        return None
    return base_url

def fetch_auth_token():
    """获取新的Authorization token"""
    global global_token, last_token_update
    
    # 检查是否需要更新token
    current_time = time.time()
    if global_token and (current_time - last_token_update) < TOKEN_EXPIRY:
        return global_token
    
    try:
        base_url = get_api_base_url()
        if not base_url:
            return None
            
        login_url = f"{base_url}/api/v1/passport/auth/login"
        
        # 从环境变量或文件获取账号密码
        email = get_env_or_file("API_EMAIL")
        password = get_env_or_file("API_PASSWORD")
        
        # 检查是否获取到凭证
        if not email or not password:
            app.logger.error("API_EMAIL 或 API_PASSWORD 未设置")
            return None
        
        login_data = {
            "email": email,
            "password": password
        }
        
        headers = {
            "content-type": "application/json",
            "user-agent": api_headers["User-Agent"]
        }
        
        app.logger.info(f"正在从 {base_url} 获取新的Authorization token...")
        response = requests.post(login_url, json=login_data, headers=headers, timeout=10)
        
        if response.status_code != 200:
            app.logger.error(f"登录失败: {response.status_code} - {response.text[:200]}")
            return None
        
        auth_data = response.json().get("data", {})
        token = auth_data.get("auth_data")
        
        if token:
            # 只显示部分token，避免在日志中暴露完整token
            app.logger.info(f"成功获取新的Authorization：{token[:30]}...")
            global_token = token
            last_token_update = current_time
            return token
        else:
            app.logger.error("响应中未找到auth_data")
            return None
            
    except Exception as e:
        app.logger.exception(f"获取token时出错: {str(e)}")
        return None

@app.route('/test')
def test():
    """测试端点"""
    base_url = get_api_base_url()
    if not base_url:
        return "服务配置错误: API_BASE_URL 未设置", 500
    return f"服务正常运行! 当前API基础URL: {base_url}"

@app.route('/get_subscribe', methods=['GET'])
def get_subscribe():
    """获取订阅内容"""
    app.logger.info("收到 /get_subscribe 请求")
    
    # 获取客户端请求的User-Agent
    client_user_agent = request.headers.get('User-Agent', api_headers['User-Agent'])
    app.logger.debug(f"客户端User-Agent: {client_user_agent}")
    
    try:
        # 获取API基础URL
        base_url = get_api_base_url()
        if not base_url:
            return jsonify({"status": "error", "message": "API基础URL未配置"}), 500
            
        # 获取或更新Authorization token
        auth_token = fetch_auth_token()
        if not auth_token:
            app.logger.error("无法获取有效的Authorization token")
            return jsonify({"status": "error", "message": "无法获取授权令牌"}), 500
        
        # 第一步：获取订阅URL
        url = f"{base_url}/api/v1/user/getSubscribe"
        headers = {**api_headers, "Authorization": auth_token}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 401:  # 未授权错误
            app.logger.warning("Token可能已过期，尝试刷新...")
            # 强制刷新token
            auth_token = fetch_auth_token()
            if auth_token:
                headers["Authorization"] = auth_token
                response = requests.get(url, headers=headers, timeout=10)
            else:
                app.logger.error("刷新token失败")
                return jsonify({"status": "error", "message": "无法刷新授权令牌"}), 500
        
        if response.status_code != 200:
            app.logger.error(f"获取订阅URL失败: {response.status_code} - {response.text[:200]}")
            return Response(
                response.content,
                status=502,
                content_type=response.headers.get('Content-Type', 'text/plain')
            )
        
        data = response.json()
        subscribe_url = data.get("data", {}).get("subscribe_url")
        if not subscribe_url:
            app.logger.error("订阅URL未找到")
            return jsonify({"status": "error", "message": "订阅URL未找到"}), 404
        
        # 第二步：请求订阅URL内容，使用客户端User-Agent
        app.logger.info(f"请求订阅内容: {subscribe_url}")
        sub_headers = {'User-Agent': client_user_agent}
        sub_response = requests.get(subscribe_url, headers=sub_headers, timeout=15)
        
        # 第三步：返回原始订阅内容
        return Response(
            sub_response.content,
            status=sub_response.status_code,
            content_type=sub_response.headers.get('Content-Type', 'text/plain')
        )
        
    except requests.exceptions.Timeout:
        app.logger.error("请求上游API超时")
        return jsonify({"status": "error", "message": "请求超时"}), 504
    except Exception as e:
        app.logger.exception(f"处理请求时出错: {str(e)}")
        return jsonify({"status": "error", "message": "内部服务器错误"}), 500

if __name__ == '__main__':
    app.logger.info("启动服务...")
    
    # 检查环境变量是否设置
    base_url = get_api_base_url()
    if not base_url:
        app.logger.error("API_BASE_URL 环境变量必须设置")
        exit(1)
        
    email = get_env_or_file("API_EMAIL")
    password = get_env_or_file("API_PASSWORD")
    
    if not email or not password:
        app.logger.error("API_EMAIL 和 API_PASSWORD 环境变量必须设置")
        exit(1)
    
    app.logger.info(f"当前API基础URL: {base_url}")
    
    # 只有在非调试模式或主进程中才预获取token
    if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        app.logger.info("预获取Authorization token...")
        if not fetch_auth_token():
            app.logger.error("无法获取初始token，服务启动失败")
            exit(1)
    
    # 生产环境关闭调试模式
    app.run(host='0.0.0.0', port=5000, debug=False)
