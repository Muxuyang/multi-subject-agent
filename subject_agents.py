"""
学科智能体基类和具体实现
每个学科智能体是一个独立的FastAPI服务
"""

from fastapi import FastAPI, HTTPException
from aip_models import TaskCommand, TaskResult, TaskStatus, TaskStatusType, Product, TextDataItem, SenderRole
from openai import OpenAI
import os
from dotenv import load_dotenv
from typing import Dict
import uvicorn

load_dotenv()


class SubjectAgent:
    """学科智能体基类"""

    def __init__(self, subject: str, subject_cn: str, port: int):
        self.subject = subject  # 学科英文名
        self.subject_cn = subject_cn  # 学科中文名
        self.port = port
        self.agent_id = f"agent_{subject}"
        self.app = FastAPI(title=f"{subject_cn}智能体")

        # 初始化大模型客户端
        self.client = OpenAI(
            api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_API_BASE")
        )
        self.model = os.getenv("LLM_MODEL", "qwen-plus")

        # 任务存储（内存）
        self.tasks: Dict[str, TaskResult] = {}

        # 注册路由
        self._register_routes()

    def _register_routes(self):
        """注册FastAPI路由"""

        @self.app.get("/health")
        async def health_check():
            """健康检查"""
            return {"status": "healthy", "agent": self.agent_id}

        @self.app.post("/rpc", response_model=TaskResult)
        async def handle_task(command: TaskCommand):
            """处理任务命令（AIP协议入口）"""
            if command.command == "start":
                return await self._handle_start(command)
            elif command.command == "get":
                return self._handle_get(command)
            elif command.command == "complete":
                return self._handle_complete(command)
            elif command.command == "cancel":
                return self._handle_cancel(command)
            else:
                raise HTTPException(status_code=400, detail=f"Unknown command: {command.command}")

    async def _handle_start(self, command: TaskCommand) -> TaskResult:
        """处理start命令：分析问题并生成答案"""
        task_id = command.task_id
        question = command.input_text

        if not question:
            result = TaskResult(
                sender_role=SenderRole.PARTNER,
                sender_id=self.agent_id,
                task_id=task_id,
                task_status=TaskStatus(
                    status=TaskStatusType.REJECTED,
                    message="缺少问题描述"
                )
            )
            self.tasks[task_id] = result
            return result

        # 调用大模型生成答案
        try:
            answer = await self._generate_answer(question)

            # 创建产出物
            product = Product(
                title=f"{self.subject_cn}角度分析",
                content=answer,
                confidence=0.85
            )

            # 返回awaiting-completion状态
            result = TaskResult(
                sender_role=SenderRole.PARTNER,
                sender_id=self.agent_id,
                task_id=task_id,
                task_status=TaskStatus(
                    status=TaskStatusType.AWAITING_COMPLETION,
                    message=f"{self.subject_cn}智能体已完成分析",
                    data_items=[TextDataItem(content=answer)]
                ),
                products=[product]
            )
            self.tasks[task_id] = result
            return result

        except Exception as e:
            result = TaskResult(
                sender_role=SenderRole.PARTNER,
                sender_id=self.agent_id,
                task_id=task_id,
                task_status=TaskStatus(
                    status=TaskStatusType.FAILED,
                    message=f"生成答案失败: {str(e)}"
                )
            )
            self.tasks[task_id] = result
            return result

    async def _generate_answer(self, question: str) -> str:
        """调用大模型生成答案"""
        system_prompt = self._get_system_prompt()

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            temperature=0.7,
            max_tokens=800
        )

        return response.choices[0].message.content

    def _get_system_prompt(self) -> str:
        """获取学科特定的系统提示词"""
        prompts = {
            "math": "你是一位资深数学教师。回答学生问题时，注重解题思路、公式推导和计算验证。用清晰的步骤讲解，必要时给出多种解法。",
            "physics": "你是一位资深物理教师。回答学生问题时，注重物理概念、定律应用和实验验证。用生活化的例子帮助理解抽象概念。",
            "chemistry": "你是一位资深化学教师。回答学生问题时，注重化学反应原理、方程式配平和实验安全。结合微观和宏观角度分析。",
            "biology": "你是一位资深生物教师。回答学生问题时，注重生命现象本质、结构与功能关系。用形象化的比喻帮助记忆。",
            "english": "你是一位资深英语教师。回答学生问题时，注重语法规则、词汇用法和表达技巧。给出例句并标注重点。",
            "chinese": "你是一位资深语文教师。回答学生问题时，注重文本理解、写作技巧和文学鉴赏。引导学生深入思考。"
        }
        return prompts.get(self.subject, f"你是一位{self.subject_cn}领域的专家。")

    def _handle_get(self, command: TaskCommand) -> TaskResult:
        """处理get命令：返回任务当前状态"""
        task_id = command.task_id
        if task_id not in self.tasks:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        return self.tasks[task_id]

    def _handle_complete(self, command: TaskCommand) -> TaskResult:
        """处理complete命令：确认任务完成"""
        task_id = command.task_id
        if task_id not in self.tasks:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        result = self.tasks[task_id]
        result.task_status.status = TaskStatusType.COMPLETED
        return result

    def _handle_cancel(self, command: TaskCommand) -> TaskResult:
        """处理cancel命令：取消任务"""
        task_id = command.task_id
        if task_id not in self.tasks:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        result = self.tasks[task_id]
        result.task_status.status = TaskStatusType.CANCELED
        return result

    def run(self):
        """启动智能体服务"""
        import sys
        sys.stdout.reconfigure(encoding='utf-8')
        print(f"{self.subject} agent starting on port {self.port}")
        uvicorn.run(self.app, host="0.0.0.0", port=self.port, log_level="info")


# 创建各学科智能体实例的工厂函数
def create_math_agent():
    return SubjectAgent("math", "数学", int(os.getenv("AGENT_MATH_PORT", 8001)))

def create_physics_agent():
    return SubjectAgent("physics", "物理", int(os.getenv("AGENT_PHYSICS_PORT", 8002)))

def create_chemistry_agent():
    return SubjectAgent("chemistry", "化学", int(os.getenv("AGENT_CHEMISTRY_PORT", 8003)))

def create_biology_agent():
    return SubjectAgent("biology", "生物", int(os.getenv("AGENT_BIOLOGY_PORT", 8004)))

def create_english_agent():
    return SubjectAgent("english", "英语", int(os.getenv("AGENT_ENGLISH_PORT", 8005)))

def create_chinese_agent():
    return SubjectAgent("chinese", "语文", int(os.getenv("AGENT_CHINESE_PORT", 8006)))


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python subject_agents.py <math|physics|chemistry|biology|english|chinese>")
        sys.exit(1)

    subject = sys.argv[1]
    agents = {
        "math": create_math_agent,
        "physics": create_physics_agent,
        "chemistry": create_chemistry_agent,
        "biology": create_biology_agent,
        "english": create_english_agent,
        "chinese": create_chinese_agent
    }

    if subject not in agents:
        print(f"未知学科: {subject}")
        sys.exit(1)

    agent = agents[subject]()
    agent.run()
