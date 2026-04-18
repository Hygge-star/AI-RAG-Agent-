from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import sys

# 将当前目录加入 sys.path，以便导入 agent 模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent.react_agent import ReactAgent

app = FastAPI(title="智扫通智能客服 API", version="1.0.0")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化全局 Agent（单例）
_agent = None

def get_agent():
    global _agent
    if _agent is None:
        _agent = ReactAgent()
    return _agent

# 请求/响应模型
class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    answer: str

# API 端点：前端会请求 /api/chat 或 /api/v1/chat
@app.post("/api/chat")
async def chat(req: ChatRequest):
    agent = get_agent()
    # 注意：你的 ReactAgent 可能有 execute_stream 或 execute 方法
    # 这里使用非流式方法，直接获取完整回答
    # 如果你的 Agent 只支持流式，可以收集所有 chunk
    try:
        # 假设 ReactAgent 有 execute 方法返回完整字符串
        # 如果没有，可以用 execute_stream 收集
        if hasattr(agent, 'execute'):
            answer = agent.execute(req.question)
        else:
            # 使用 execute_stream 收集
            chunks = []
            for chunk in agent.execute_stream(req.question):
                chunks.append(chunk)
            answer = "".join(chunks)
        return ChatResponse(answer=answer)
    except Exception as e:
        return ChatResponse(answer=f"处理出错：{str(e)}")

# 健康检查
@app.get("/api/health")
def health():
    return {"status": "ok"}

# ========== 托管前端静态文件 ==========
FRONTEND_ROOT = "./frontend/dist"   # 请确保这个路径下有 index.html

if os.path.exists(FRONTEND_ROOT):
    # 挂载静态资源目录（如果有 assets 文件夹）
    assets_path = os.path.join(FRONTEND_ROOT, "assets")
    if os.path.exists(assets_path):
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")

    @app.get("/")
    async def root():
        return FileResponse(os.path.join(FRONTEND_ROOT, "index.html"))

    # 兜底路由：支持前端路由
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            # API 请求不应由静态文件处理，返回 404
            return {"detail": "Not Found"}, 404
        file_path = os.path.join(FRONTEND_ROOT, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_ROOT, "index.html"))
else:
    @app.get("/")
    async def root():
        return {"message": "Frontend not found. Please build and copy to ./frontend/dist"}