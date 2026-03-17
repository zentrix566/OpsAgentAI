# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OpsAgentAI (also called OpsPilot) is an intelligent DevOps monitoring tool that automatically detects and diagnoses GitHub Actions pipeline failures using AI. It:
- Listens for GitHub webhook events on pipeline completion
- Detects failures automatically
- Fetches failed job logs from GitHub API
- Sends logs to Dify AI for analysis
- Notifies the team via Feishu (Lark) webhook with AI-generated diagnostic suggestions

## Architecture

The project is a minimal single-file Flask application:

```
┌─────────────────┐     ┌──────────────┐     ┌─────────┐     ┌────────────┐
│ GitHub Webhook  │────▶│ Flask App    │────▶│ GitHub  │────▶│  Logs      │
│                 │     │  (app.py)    │     │ API     │     │            │
└─────────────────┘     └──────────────┘     └─────────┘     └────────────┘
                              │
                              ▼
┌────────────┐     ┌──────────────────┐     ┌────────────────┐
│  Dify AI   │◀────│  App analyzes    │────▶│  Feishu/Lark   │
│  Analysis  │     │  logs with AI    │     │  Notification  │
└────────────┘     └──────────────────┘     └────────────────┘
```

**Main Components:**
- `app.py`: The entire application - contains webhook handler, GitHub API client, Dify API client, and Feishu notification
- Flask web server listens on port 5000
- Single endpoint: `/webhook` (POST) for GitHub events

## Configuration

Configuration is currently hardcoded in `app.py` (lines 12-14), with comments suggesting using environment variables:

- `GITHUB_TOKEN`: GitHub Personal Access Token with repo scope for fetching job logs
- `DIFY_API_KEY`: API key for Dify AI completion service
- `NOTIFY_WEBHOOK`: Feishu/Lark bot webhook URL

## Common Commands

### Run the application
```bash
python app.py
```
Server starts at `http://0.0.0.0:5000`

### Install dependencies
```bash
pip install flask requests
```

## Development Notes

- The code truncates logs to last 2000 characters to avoid exceeding AI token limits (app.py:44)
- Uses blocking response mode from Dify API - waits for analysis before returning response to GitHub
- No authentication on webhook endpoint - should be added for production use
- No requirements.txt - dependencies are `flask` and `requests`
- All logic is in a single file - keep it simple when modifying
