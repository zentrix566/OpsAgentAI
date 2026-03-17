import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# ================= 环境变量获取 =================
# 建议在 Linux 环境中执行: 
# export GITHUB_TOKEN="你的Token"
# export DIFY_API_KEY="你的Key"
# export NOTIFY_WEBHOOK="你的钉钉地址"

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
DIFY_API_KEY = os.getenv("DIFY_API_KEY")
NOTIFY_WEBHOOK = os.getenv("NOTIFY_WEBHOOK")

# 检查必要变量是否存在
if not all([GITHUB_TOKEN, DIFY_API_KEY, NOTIFY_WEBHOOK]):
    print("❌ 错误: 请确保环境变量 GITHUB_TOKEN, DIFY_API_KEY, NOTIFY_WEBHOOK 已设置！")

# Dify 默认接口地址（如果是私有部署，请修改此项或同样改为环境变量获取）
DIFY_URL = os.getenv("DIFY_URL", "https://api.dify.ai/v1/workflow/run")

# ================= 核心逻辑 =================

def get_github_log(repo_name, job_id):
    """从 GitHub API 获取 Job 的最后一段日志"""
    url = f"https://api.github.com/repos/{repo_name}/actions/jobs/{job_id}/logs"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            # 截取最后 2000 字符，避免超出 LLM Token 限制
            return response.text[-2000:]
        return f"无法获取日志，状态码: {response.status_code}"
    except Exception as e:
        return f"请求 GitHub API 出错: {str(e)}"

def ask_dify_ai(error_log, repo_name):
    """调用 Dify 工作流进行诊断"""
    headers = {
        "Authorization": f"Bearer {DIFY_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": {
            "error_logs": error_log,
            "project_name": repo_name
        },
        "response_mode": "blocking",
        "user": "OpsPilot-System"
    }
    try:
        res = requests.post(DIFY_URL, json=payload, headers=headers, timeout=30)
        print(f"Dify 状态码: {res.status_code}") # 添加这一行
        print(f"Dify 响应内容: {res.text}")      # 添加这一行
        res_data = res.json()
        return res_data.get('data', {}).get('outputs', {}).get('text', "AI 未返回有效诊断信息")
    except Exception as e:
        print(f"请求 Dify 异常: {str(e)}")        # 添加这一行
        return f"Dify 接口调用失败: {str(e)}"

def push_notification(repo_name, diagnosis, job_url):
    """推送消息到钉钉"""
    content = (
        f"### ⚠️ OpsPilot 故障预警\n\n"
        f"**项目**: {repo_name}\n\n"
        f"**AI 诊断建议**:\n{diagnosis}\n\n"
        f"[点击查看流水线详情]({job_url})"
    )
    payload = {
        "msgtype": "markdown",
        "markdown": {"title": "流水线失败预警", "text": content}
    }
    try:
        requests.post(NOTIFY_WEBHOOK, json=payload, timeout=10)
    except Exception as e:
        print(f"推送通知失败: {str(e)}")

@app.route('/webhook', methods=['POST'])
def github_webhook():
    data = request.json
    
    # 匹配 GitHub Actions 的 check_run 失败事件
    if data.get("action") == "completed" and data.get("check_run", {}).get("conclusion") == "failure":
        check_run = data['check_run']
        repo_name = data['repository']['full_name']
        job_id = check_run['id']
        job_url = check_run['html_url']
        
        print(f"🚀 检测到 {repo_name} 失败，开始分析...")
        
        logs = get_github_log(repo_name, job_id)
        diagnosis = ask_dify_ai(logs, repo_name)
        push_notification(repo_name, diagnosis, job_url)
        
        return "Success", 200

    return "Ignored", 200

if __name__ == '__main__':
    # 默认监听 5000 端口
    app.run(host='0.0.0.0', port=5000)