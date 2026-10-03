"""
调度中心（Orchestrator）- 简化版
内置所有学科智能体逻辑，直接调用智谱API
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from aip_models import TaskCommand, TaskResult, CommandType, SenderRole, TaskStatus, TaskStatusType, Product, TextDataItem
from openai import OpenAI
import asyncio
from typing import List, Dict, Tuple, Optional
import os
from dotenv import load_dotenv
import jieba
import re
from datetime import datetime
import json

load_dotenv()

# 初始化智谱AI客户端
llm_client = OpenAI(
    api_key=os.getenv("ZHIPU_API_KEY"),
    base_url="https://open.bigmodel.cn/api/paas/v4"
)
LLM_MODEL = "glm-4-flash"  # 智谱AI的快速模型

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


# 学科智能体配置（移除URL，只保留关键词和系统提示词）
AGENTS = {
    "math": {
        "name": "数学",
        "keywords": ["方程", "计算", "几何", "函数", "数学", "解题", "公式", "数字", "算", "图形", "角度", "面积", "体积"],
        "system_prompt": "你是一位资深数学教师。回答学生问题时，注重解题思路、公式推导和计算验证。用清晰的步骤讲解，必要时给出多种解法。"
    },
    "physics": {
        "name": "物理",
        "keywords": ["力", "能量", "运动", "电路", "物理", "速度", "加速度", "牛顿", "电", "磁", "光", "声", "热"],
        "system_prompt": "你是一位资深物理教师。回答学生问题时，注重物理概念、定律应用和实验验证。用生活化的例子帮助理解抽象概念。"
    },
    "chemistry": {
        "name": "化学",
        "keywords": ["反应", "元素", "分子", "化学", "实验", "方程式", "酸", "碱", "盐", "氧化", "还原", "离子"],
        "system_prompt": "你是一位资深化学教师。回答学生问题时，注重化学反应原理、方程式配平和实验安全。结合微观和宏观角度分析。"
    },
    "biology": {
        "name": "生物",
        "keywords": ["细胞", "遗传", "进化", "生物", "DNA", "蛋白质", "光合作用", "呼吸", "生态", "物种"],
        "system_prompt": "你是一位资深生物教师。回答学生问题时，注重生命现象本质、结构与功能关系。用形象化的比喻帮助记忆。"
    },
    "english": {
        "name": "英语",
        "keywords": ["英语", "语法", "单词", "句子", "翻译", "词汇", "时态", "english"],
        "system_prompt": "你是一位资深英语教师。回答学生问题时，注重语法规则、词汇用法和表达技巧。给出例句并标注重点。"
    },
    "chinese": {
        "name": "语文",
        "keywords": ["语文", "作文", "古诗", "文言文", "阅读", "理解", "修辞", "成语", "诗歌"],
        "system_prompt": "你是一位资深语文教师。回答学生问题时，注重文本理解、写作技巧和文学鉴赏。引导学生深入思考。"
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
    """
    调用单个智能体（内置版本，直接调用智谱API）
    """
    agent_config = AGENTS[subject]
    agent_id = f"agent_{subject}"

    try:
        # 直接调用智谱API生成答案
        response = llm_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": agent_config["system_prompt"]},
                {"role": "user", "content": question}
            ],
            temperature=0.7,
            max_tokens=800
        )

        answer = response.choices[0].message.content

        # 创建产出物（符合ACPs Product标准）
        product = Product(
            id=f"{agent_id}_{task_id}",
            name=f"{agent_config['name']}角度分析",
            dataItems=[
                {
                    "type": "text",
                    "content": answer,
                    "confidence": 0.85
                }
            ]
        )

        # 返回TaskResult
        result = TaskResult(
            senderRole=SenderRole.PARTNER,
            senderId=agent_id,
            taskId=f"{task_id}_{subject}",
            status=TaskStatus(
                state=TaskStatusType.AWAITING_COMPLETION,
                message=f"{agent_config['name']}智能体已完成分析"
            ).model_dump(),
            products=[product]
        )

        return (subject, result)

    except Exception as e:
        print(f"❌ {agent_config['name']}智能体调用失败: {str(e)}")
        # 返回失败结果
        result = TaskResult(
            senderRole=SenderRole.PARTNER,
            senderId=agent_id,
            taskId=f"{task_id}_{subject}",
            status=TaskStatus(
                state=TaskStatusType.FAILED,
                message=f"生成答案失败: {str(e)}"
            ).model_dump(),
            products=[]
        )
        return (subject, result)


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
            # products是字典列表，从dataItems中提取content
            product_dict = result.products[0]
            if 'dataItems' in product_dict and len(product_dict['dataItems']) > 0:
                subject_answers[AGENTS[subject]["name"]] = product_dict['dataItems'][0]['content']
            else:
                subject_answers[AGENTS[subject]["name"]] = "[无内容]"
        else:
            subject_answers[AGENTS[subject]["name"]] = f"[{result.status['message']}]"

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
        agents_info.append({
            "id": f"agent_{subject}",
            "name": config["name"],
            "subject": subject,
            "status": "online",  # 内置智能体始终在线
            "keywords": config["keywords"]
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
        if command.command == CommandType.START:
            # 提取用户问题
            user_query = ""
            if command.dataItems:
                for item in command.dataItems:
                    if isinstance(item, TextDataItem):
                        user_query = item.text
                        break
                    elif isinstance(item, dict) and 'text' in item:
                        user_query = item['text']
                        break

            if not user_query:
                return TaskResult(
                    senderRole=SenderRole.PARTNER,
                    senderId="orchestrator",
                    taskId=command.taskId,
                    status=TaskStatus(
                        state=TaskStatusType.FAILED,
                        message="未找到有效的问题文本"
                    ).model_dump(),
                    products=[]
                )

            # 分析问题并调用智能体
            involved_subjects = analyze_question(user_query)
            tasks = [call_agent(subject, user_query, command.taskId) for subject in involved_subjects]
            results_list = await asyncio.gather(*tasks)
            results = dict(results_list)

            # 协商融合答案
            negotiated_answer = await negotiate_answers(user_query, results)

            # 返回AIP格式结果
            product = Product(
                title="多学科协商答案",
                content=negotiated_answer,
                confidence=0.9
            )

            return TaskResult(
                senderRole=SenderRole.PARTNER,
                senderId="orchestrator",
                taskId=command.taskId,
                status=TaskStatus(
                    state=TaskStatusType.AWAITING_COMPLETION,
                    message="协商完成"
                ).model_dump(),
                products=[product]
            )

        elif command.command == CommandType.COMPLETE:
            # 确认完成
            return TaskResult(
                senderRole=SenderRole.PARTNER,
                senderId="orchestrator",
                taskId=command.taskId,
                status=TaskStatus(
                    state=TaskStatusType.COMPLETED,
                    message="任务已完成"
                ).model_dump(),
                products=[]
            )

        elif command.command == CommandType.GET:
            # 获取任务状态
            return TaskResult(
                senderRole=SenderRole.PARTNER,
                senderId="orchestrator",
                taskId=command.taskId,
                status=TaskStatus(
                    state=TaskStatusType.WORKING,
                    message="任务进行中"
                ).model_dump(),
                products=[]
            )

        else:
            # 不支持的命令
            return TaskResult(
                senderRole=SenderRole.PARTNER,
                senderId="orchestrator",
                taskId=command.taskId,
                status=TaskStatus(
                    state=TaskStatusType.REJECTED,
                    message=f"不支持的命令: {command.command}"
                ).model_dump(),
                products=[]
            )

    except Exception as e:
        return TaskResult(
            senderRole=SenderRole.PARTNER,
            senderId="orchestrator",
            taskId=command.taskId,
            status=TaskStatus(
                state=TaskStatusType.FAILED,
                message=f"处理失败: {str(e)}"
            ).model_dump(),
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
