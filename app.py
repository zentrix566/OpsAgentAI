from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# 配置信息（建议通过环境变量注入）
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
DIFY_API_KEY = os.getenv("DIFY_API_KEY")
NOTIFY_WEBHOOK = os.getenv("NOTIFY_WEBHOOK") # 钉钉/企微地址



@app.route('/webhook', methods=['POST'])
def handle_webhook():
    data = request.json
    
    # 1. 识别 GitHub Actions 流水线失败事件
    # 逻辑：check_run 完成且结论为 failure
    if data.get("action") == "completed" and data.get("check_run", {}).get("conclusion") == "failure":
        repo_name = data['repository']['full_name']
        run_id = data['check_run']['check_suite']['id']
        job_id = data['check_run']['id']
        
        print(f"检测到项目 {repo_name} 流水线失败，正在抓取日志...")
        
        # 2. 调用 GitHub API 获取最后 50 行日志
        log_content = get_github_logs(repo_name, job_id)
        
        # 3. 将日志发送给 Dify 进行分析
        analysis = ask_dify_ai(log_content)
        
        # 4. 发送结果到通知群
        send_notification(repo_name, analysis)
        
    return jsonify({"status": "received"}), 200

def get_github_logs(repo, job_id):
    url = f"https://api.github.com/repos/{repo}/actions/jobs/{job_id}/logs"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    response = requests.get(url, headers=headers)
    # 截取最后 2000 个字符发送给 AI，避免超过 Token 限制
    return response.text[-2000:]

def ask_dify_ai(logs):
    url = "https://api.dify.ai/v1/completion-messages" # 假设使用工作流模式
    headers = {"Authorization": f"Bearer {DIFY_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "inputs": {"logs": logs},
        "response_mode": "blocking",
        "user": "OpsPilot-System"
    }
    res = requests.post(url, json=payload, headers=headers)
    return res.json().get('answer', 'AI 分析失败')

def send_notification(repo, content):
    msg = {
        "msgtype": "markdown",
        "markdown": {
            "title": "OpsPilot 故障预警",
            "text": f"### ⚠️ 项目 {repo} 构建失败\n**AI 诊断建议：**\n\n{content}"
        }
    }
    requests.post(NOTIFY_WEBHOOK, json=msg)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)