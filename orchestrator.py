"""
调度中心（Orchestrator）
负责问题分析、智能体召集、协商融合
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from aip_models import TaskCommand, TaskResult, CommandType, SenderRole
import httpx
import asyncio
from typing import List, Dict, Tuple, Optional
import os
from dotenv import load_dotenv
import jieba
import re
from datetime import datetime
import json

load_dotenv()

app = FastAPI(title="多学科智能体协商调度中心")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")


class QuestionRequest(BaseModel):
    """用户问题请求"""
    question: str


class NegotiationResponse(BaseModel):
    """协商响应"""
    question: str
    involved_subjects: List[str]
    subject_answers: Dict[str, str]
    negotiated_answer: str
    task_id: str
    timestamp: str


# 学科智能体配置
AGENTS = {
    "math": {
        "name": "数学",
        "url": f"http://localhost:{os.getenv('AGENT_MATH_PORT', 8001)}/rpc",
        "keywords": ["方程", "计算", "几何", "函数", "数学", "解题", "公式", "数字", "算", "图形", "角度", "面积", "体积"]
    },
    "physics": {
        "name": "物理",
        "url": f"http://localhost:{os.getenv('AGENT_PHYSICS_PORT', 8002)}/rpc",
        "keywords": ["力", "能量", "运动", "电路", "物理", "速度", "加速度", "牛顿", "电", "磁", "光", "声", "热"]
    },
    "chemistry": {
        "name": "化学",
        "url": f"http://localhost:{os.getenv('AGENT_CHEMISTRY_PORT', 8003)}/rpc",
        "keywords": ["反应", "元素", "分子", "化学", "实验", "方程式", "酸", "碱", "盐", "氧化", "还原", "离子"]
    },
    "biology": {
        "name": "生物",
        "url": f"http://localhost:{os.getenv('AGENT_BIOLOGY_PORT', 8004)}/rpc",
        "keywords": ["细胞", "遗传", "进化", "生物", "DNA", "蛋白质", "光合作用", "呼吸", "生态", "物种"]
    },
    "english": {
        "name": "英语",
        "url": f"http://localhost:{os.getenv('AGENT_ENGLISH_PORT', 8005)}/rpc",
        "keywords": ["英语", "语法", "单词", "句子", "翻译", "词汇", "时态", "english"]
    },
    "chinese": {
        "name": "语文",
        "url": f"http://localhost:{os.getenv('AGENT_CHINESE_PORT', 8006)}/rpc",
        "keywords": ["语文", "作文", "古诗", "文言文", "阅读", "理解", "修辞", "成语", "诗歌"]
    }
}


def analyze_question(question: str) -> List[str]:
    """
    分析问题涉及的学科
    基于关键词匹配
    """
    question_lower = question.lower()
    words = jieba.lcut(question)

    involved = []
    for subject, config in AGENTS.items():
        # 关键词匹配
        for keyword in config["keywords"]:
            if keyword in question or keyword in " ".join(words):
                involved.append(subject)
                break

    # 如果没有匹配到任何学科，默认调用数学和语文
    if not involved:
        involved = ["math", "chinese"]

    return involved


async def call_agent(subject: str, question: str, task_id: str) -> Tuple[str, TaskResult]:
    """调用单个智能体"""
    agent_config = AGENTS[subject]

    command = TaskCommand(
        sender_role=SenderRole.LEADER,
        sender_id="orchestrator",
        command=CommandType.START,
        task_id=f"{task_id}_{subject}",
        input_text=question
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                agent_config["url"],
                json=command.model_dump(mode="json")
            )
            response.raise_for_status()
            result = TaskResult(**response.json())
            return subject, result
    except Exception as e:
        print(f"调用{agent_config['name']}智能体失败: {str(e)}")
        # 返回失败结果
        from aip_models import TaskStatus, TaskStatusType
        failed_result = TaskResult(
            sender_role=SenderRole.PARTNER,
            sender_id=f"agent_{subject}",
            task_id=f"{task_id}_{subject}",
            task_status=TaskStatus(
                status=TaskStatusType.FAILED,
                message=str(e)
            )
        )
        return subject, failed_result


async def negotiate_answers(question: str, results: Dict[str, TaskResult]) -> str:
    """
    协商融合多个智能体的答案
    策略：根据问题主题确定主学科，其他学科补充
    """
    # 过滤失败的结果
    valid_results = {
        subject: result for subject, result in results.items()
        if result.products and len(result.products) > 0
    }

    if not valid_results:
        return "抱歉，所有智能体都未能给出有效答案。"

    if len(valid_results) == 1:
        # 只有一个智能体，直接返回其答案
        subject = list(valid_results.keys())[0]
        return valid_results[subject].products[0].content

    # 多智能体协商：拼接答案，标注来源
    negotiated = f"【综合分析】针对问题「{question}」，各学科智能体协商结果如下：\n\n"

    for subject, result in valid_results.items():
        agent_name = AGENTS[subject]["name"]
        answer = result.products[0].content
        negotiated += f"## {agent_name}角度\n{answer}\n\n"

    # 添加协商总结
    negotiated += "---\n💡 **协商总结**：以上是各学科智能体基于各自专业视角的分析。"
    negotiated += "建议从多角度理解问题，综合各方观点形成完整认知。"

    return negotiated


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "orchestrator"}


@app.post("/ask", response_model=NegotiationResponse)
async def ask_question(request: QuestionRequest):
    """
    接收用户问题，协调多智能体回答
    """
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")

    # 生成任务ID
    task_id = f"task_{int(datetime.now().timestamp() * 1000)}"

    # 1. 分析问题，确定涉及的学科
    involved_subjects = analyze_question(question)
    print(f"📋 问题涉及学科: {[AGENTS[s]['name'] for s in involved_subjects]}")

    # 2. 并行调用相关智能体
    tasks = [call_agent(subject, question, task_id) for subject in involved_subjects]
    results_list = await asyncio.gather(*tasks)
    results = dict(results_list)

    # 3. 提取各智能体的答案
    subject_answers = {}
    for subject, result in results.items():
        if result.products and len(result.products) > 0:
            subject_answers[AGENTS[subject]["name"]] = result.products[0].content
        else:
            subject_answers[AGENTS[subject]["name"]] = f"[{result.task_status.message}]"

    # 4. 协商融合答案
    negotiated_answer = await negotiate_answers(question, results)

    return NegotiationResponse(
        question=question,
        involved_subjects=[AGENTS[s]["name"] for s in involved_subjects],
        subject_answers=subject_answers,
        negotiated_answer=negotiated_answer,
        task_id=task_id,
        timestamp=datetime.now().isoformat()
    )


@app.get("/agents")
async def list_agents():
    """列出所有可用智能体"""
    agents_info = []
    for subject, config in AGENTS.items():
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(config["url"].replace("/rpc", "/health"))
                status = "online" if response.status_code == 200 else "offline"
        except:
            status = "offline"

        agents_info.append({
            "subject": subject,
            "name": config["name"],
            "status": status,
            "url": config["url"]
        })

    return {"agents": agents_info}


# ===== ACPs 协议接口 =====

@app.get("/health")
async def health_check():
    """健康检查接口（ACPs规范要求）"""
    return JSONResponse({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "multi-subject-tutor-orchestrator"
    })


@app.get("/acs/metadata")
async def get_metadata():
    """返回ACS元数据（智能体能力描述）"""
    metadata_path = os.path.join(os.path.dirname(__file__), "acs_metadata.json")
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    return metadata


@app.post("/aip/rpc")
async def aip_rpc_handler(command: TaskCommand):
    """
    AIP协议RPC接口
    处理来自Leader的任务命令（梧桐平台接入）
    """
    try:
        if command.command == CommandType.Start:
            # 提取用户问题
            user_query = ""
            if command.dataItems:
                for item in command.dataItems:
                    if hasattr(item, 'text'):
                        user_query = item.text
                        break

            if not user_query:
                return TaskResult(
                    id=f"result-{command.id}",
                    sentAt=datetime.now().isoformat(),
                    senderRole=SenderRole.Partner,
                    senderId="orchestrator",
                    taskId=command.taskId,
                    sessionId=command.sessionId,
                    status={"state": "failed", "stateChangedAt": datetime.now().isoformat()},
                    products=[]
                )

            # 调用内部协商流程
            result = await negotiate({"question": user_query})

            # 转换为AIP格式返回
            return TaskResult(
                id=f"result-{command.taskId}",
                sentAt=datetime.now().isoformat(),
                senderRole=SenderRole.Partner,
                senderId="orchestrator",
                taskId=command.taskId,
                sessionId=command.sessionId,
                status={
                    "state": "awaiting-completion",
                    "stateChangedAt": datetime.now().isoformat()
                },
                products=[{
                    "id": f"product-{command.taskId}",
                    "name": "协商结果",
                    "dataItems": [{
                        "type": "text",
                        "text": result["finalAnswer"]
                    }]
                }]
            )

        elif command.command == CommandType.Complete:
            # 确认完成
            return TaskResult(
                id=f"result-{command.id}",
                sentAt=datetime.now().isoformat(),
                senderRole=SenderRole.Partner,
                senderId="orchestrator",
                taskId=command.taskId,
                sessionId=command.sessionId,
                status={
                    "state": "completed",
                    "stateChangedAt": datetime.now().isoformat()
                },
                products=[]
            )

        elif command.command == CommandType.Get:
            # 获取任务状态
            return TaskResult(
                id=f"result-{command.id}",
                sentAt=datetime.now().isoformat(),
                senderRole=SenderRole.Partner,
                senderId="orchestrator",
                taskId=command.taskId,
                sessionId=command.sessionId,
                status={
                    "state": "working",
                    "stateChangedAt": datetime.now().isoformat()
                },
                products=[]
            )

        else:
            # 不支持的命令
            return TaskResult(
                id=f"result-{command.id}",
                sentAt=datetime.now().isoformat(),
                senderRole=SenderRole.Partner,
                senderId="orchestrator",
                taskId=command.taskId,
                sessionId=command.sessionId,
                status={
                    "state": "rejected",
                    "stateChangedAt": datetime.now().isoformat()
                },
                products=[]
            )

    except Exception as e:
        return TaskResult(
            id=f"result-{command.id}",
            sentAt=datetime.now().isoformat(),
            senderRole=SenderRole.Partner,
            senderId="orchestrator",
            taskId=command.taskId,
            sessionId=command.sessionId or "",
            status={
                "state": "failed",
                "stateChangedAt": datetime.now().isoformat(),
                "message": str(e)
            },
            products=[]
        )


if __name__ == "__main__":
    import uvicorn
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    # Railway uses PORT, fallback to ORCHESTRATOR_PORT for local dev
    port = int(os.getenv("PORT", os.getenv("ORCHESTRATOR_PORT", "8000")))
    print(f"Orchestrator starting on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
