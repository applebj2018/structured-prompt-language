import requests
import json
import yaml
import re
from typing import Dict, List, Optional

# ================== Ollama Client with Diagnostics ==================
class OllamaClient:
    def __init__(self, model="qwen3.5:9b", base_url="http://localhost:11434", debug=False, timeout=60):
        self.model = model
        self.base_url = base_url.rstrip('/')
        self.debug = debug
        self.timeout = timeout
        self.available = self._check_availability()

    def _check_availability(self):
        """检查 Ollama 服务是否可用，并列出可用模型"""
        try:
            resp = requests.get(self.base_url, timeout=3)
            if resp.status_code != 200:
                return False

            tags_url = f"{self.base_url}/api/tags"
            tags_resp = requests.get(tags_url, timeout=5)
            if tags_resp.status_code == 200:
                models = [m["name"] for m in tags_resp.json().get("models", [])]
                if self.model not in models:
                    print(f"[Ollama 警告] 模型 '{self.model}' 未在本地找到。可用模型: {models}")
                else:
                    if self.debug:
                        print(f"[Ollama Debug] 找到模型: {self.model}")
            return True
        except Exception as e:
            print(f"[Ollama 错误] 无法连接到 Ollama 服务: {e}")
            return False

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.available:
            return ""
        try:
            url = f"{self.base_url}/api/generate"
            payload = {
                "model": self.model,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "options": {"temperature": 0.7}
            }
            headers = {"Content-Type": "application/json"}

            if self.debug:
                print(f"[Ollama Debug] 请求 URL: {url}")
                print(f"[Ollama Debug] 请求模型: {self.model}")
                print(f"[Ollama Debug] 请求 prompt 前100字符: {prompt[:100]}...")

            response = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            if self.debug:
                print(f"[Ollama Debug] 响应状态码: {response.status_code}")
                print(f"[Ollama Debug] 响应内容前200字符: {response.text[:200]}")

            response.raise_for_status()
            return response.json().get("response", "")
        except requests.exceptions.Timeout:
            print(f"[Ollama 错误] 请求超时（{self.timeout}秒）")
        except requests.exceptions.HTTPError as e:
            error_detail = e.response.text if e.response else "无详细信息"
            print(f"[Ollama HTTP 错误] {e}\n响应内容: {error_detail}")
        except Exception as e:
            print(f"[Ollama 错误] {e}")
        return ""

    def generate_json(self, prompt: str, system_prompt: str = "") -> dict:
        """要求模型返回 JSON 格式，自动清理 Markdown 代码块"""
        response = self.generate(prompt, system_prompt)
        if not response:
            return {}

        # 清理 Markdown 代码块（```json ... ```）
        cleaned = re.sub(r'```json\s*|\s*```', '', response)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # 尝试提取 JSON 对象或数组
        json_match = re.search(r'(\{.*\}|\[.*\])', cleaned, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        if self.debug:
            print(f"[Ollama Debug] 无法解析 JSON，原始响应: {response[:200]}")
        return {}

# ================== Technique Matcher ==================
class TechniqueMatcher:
    def __init__(self):
        self.keyword_map = {
            "角色扮演": ["作为", "专家", "身份", "角色"],
            "步骤清晰": ["步骤", "首先", "然后", "流程"],
            "限定条件": ["必须", "不能", "禁止", "仅限于"],
            "原因解释": ["为什么", "理由", "解释"],
            "伪代码": ["逻辑", "算法", "伪代码"],
            "目标驱动": ["目标", "目的是", "为了"],
            "明确输出格式": ["格式", "JSON", "表格", "Markdown"],
            "让AI提问": ["信息不足", "请问我"],
            "输出细致程度": ["健壮", "详细", "简洁"],
            "压缩/总结": ["总结", "概括", "精简"],
            "查询最新技术": ["最新", "当前", "2025"],
            "性格特点": ["幽默", "严谨", "通俗"],
            "格式化提示词": ["系统指令", "用户指令"],
            "分段专注": ["长文本", "太长"],
            "合并": ["同时", "一并"],
            "排除不可行方案": ["剔除", "排除", "不可行"],
            "个性喜好": ["偏好", "喜欢"],
            "让AI给例子": ["举个例子", "示范"],
            "先生成提示词": ["优化提问"],
            "外部工具": ["联网", "搜索"],
        }

    def match(self, text: str) -> List[str]:
        techniques = set()
        text_lower = text.lower()
        for technique, keywords in self.keyword_map.items():
            if any(k in text_lower for k in keywords):
                techniques.add(technique)
        techniques.add("目标驱动")
        return list(techniques)

# ================== Task Classifier (您关注的完整类) ==================
class TaskClassifier:
    """识别任务类型，用于自动补全角色上下文"""
    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        self.ollama = ollama_client
        # 基于关键词的快速分类（备选）
        self.keywords = {
            "编程": ["代码", "程序", "开发", "编程", "bug", "重构", "算法", "函数", "类"],
            "写作": ["写", "文章", "报告", "邮件", "文案", "创意", "故事"],
            "分析": ["分析", "评估", "检查", "审查", "总结", "报告"],
            "设计": ["设计", "架构", "方案", "流程图", "原型"],
            "问答": ["问题", "回答", "解释", "帮助"],
        }

    def classify(self, text: str) -> str:
        """返回任务类型，如 '编程', '写作', '分析', '设计', '问答', '通用'"""
        if self.ollama and self.ollama.available:
            prompt = f"""根据以下任务描述，判断它属于哪种类型（只输出一个词）：
可选类型：编程、写作、分析、设计、问答、通用
描述：{text}
输出："""
            resp = self.ollama.generate(prompt).strip().lower()
            if resp in ["编程", "写作", "分析", "设计", "问答", "通用"]:
                return resp
        # 关键词匹配
        text_lower = text.lower()
        for task_type, words in self.keywords.items():
            if any(w in text_lower for w in words):
                return task_type
        return "通用"

# ================== Gap Detector ==================
class GapDetector:
    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        self.ollama = ollama_client

    def detect(self, nl_input: str, techniques: List[str]) -> List[str]:
        gaps = []
        if "角色扮演" in techniques and "作为" not in nl_input and "专家" not in nl_input:
            gaps.append("您希望设定什么角色来处理这个任务？")
        if "明确输出格式" in techniques:
            if not any(fmt in nl_input for fmt in ["JSON", "表格", "Markdown", "列表"]):
                gaps.append("您希望输出什么格式？")
        if len(nl_input) < 20:
            gaps.append("任务描述较简短，能否补充更多细节？")
        return gaps

    def suggest_role_context(self, task_type: str, nl_input: str) -> str:
        """根据任务类型自动生成丰富的角色描述，失败时返回默认值"""
        if self.ollama and self.ollama.available:
            prompt = f"""任务类型：{task_type}
任务描述：{nl_input}
请为这个任务生成一个具体的角色描述，包括经验、行业背景、专长等，例如“资深Java工程师，10年经验，擅长微服务架构和安全编码”。只输出角色描述本身。"""
            role = self.ollama.generate(prompt).strip()
            if role:
                return role
        # 默认角色
        default_roles = {
            "编程": "资深软件工程师，5年以上开发经验，熟悉系统架构和代码优化",
            "写作": "专业文案写手，擅长清晰表达和创意写作",
            "分析": "数据分析专家，精通数据解读和报告撰写",
            "设计": "高级架构师，有丰富的系统设计和工程经验",
            "问答": "知识渊博的助手，擅长解答问题",
            "通用": "专业助理，熟悉各类任务处理"
        }
        return default_roles.get(task_type, "专业助理")

# ================== Interactive Prompter ==================
class InteractivePrompter:
    def __init__(self):
        self.answers = {}

    def ask(self, gaps: List[str]) -> Dict[str, str]:
        for gap in gaps:
            print(f"[编译器] {gap}")
            answer = input("[用户] ").strip()
            self.answers[gap] = answer
        return self.answers

# ================== SPL Generator ==================
class SPLGenerator:
    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        self.ollama = ollama_client
        self.detector = GapDetector(ollama_client)

    def _convert_input_params(self, raw_dict: dict) -> dict:
        """将模型返回的输入参数转换为字段名->类型的映射"""
        if not raw_dict:
            return {"user_input": "String"}

        # 如果已经是扁平映射，直接返回
        if all(isinstance(v, str) for v in raw_dict.values()):
            return raw_dict

        # 如果包含 "parameters" 列表
        if "parameters" in raw_dict and isinstance(raw_dict["parameters"], list):
            result = {}
            for param in raw_dict["parameters"]:
                if isinstance(param, dict) and "name" in param and "type" in param:
                    result[param["name"]] = param["type"]
            if result:
                return result

        return {"user_input": "String"}

    def generate(self, nl_input: str, techniques: List[str], answers: Dict[str, str], task_type: str) -> str:
        # 1. 角色
        role = ""
        for q, a in answers.items():
            if "角色" in q:
                role = a.replace(" ", "_")
                break
        if not role:
            role = self.detector.suggest_role_context(task_type, nl_input)

        # 2. 输出格式
        output_format = "Text"
        for q, a in answers.items():
            if "格式" in q:
                output_format = a.strip().upper()
                break

        # 3. 输入接口推断
        input_fields = {"user_input": "String"}
        if self.ollama and self.ollama.available:
            prompt = f"""任务描述：{nl_input}
请推断该任务需要哪些输入参数（名称和类型）。类型可以是 String, Integer, Float, Boolean, List, JSON, Image 等。
可以返回两种格式之一：
1. 扁平对象 {{"参数名": "类型"}}
2. 对象包含 "parameters" 列表，每个元素有 "name" 和 "type"
只返回 JSON。"""
            extracted = self.ollama.generate_json(prompt)
            if extracted:
                input_fields = self._convert_input_params(extracted)

        # 4. 协议伪代码生成（优化版：要求简洁，避免过多实现细节）
        protocol_code = ""
        if self.ollama and self.ollama.available:
            prompt = f"""任务描述：{nl_input}
请将其转化为简洁、结构化的伪代码步骤。使用 Python 风格的缩进，每行描述一个主要步骤，避免过于详细的实现细节（如异常处理、数据循环等）。只输出伪代码块。"""
            protocol_code = self.ollama.generate(prompt)
        # 清理可能的 Markdown 代码块标记
        if protocol_code:
            protocol_code = re.sub(r'^```\w*\n', '', protocol_code, flags=re.MULTILINE)
            protocol_code = re.sub(r'\n```$', '', protocol_code, flags=re.MULTILINE)
        if not protocol_code.strip():
            # 规则生成基础协议
            protocol_code = f"""def process(input):
    # 步骤1: 理解任务需求
    understand_task("{nl_input}")
    # 步骤2: 收集相关资料
    research = gather_information()
    # 步骤3: 生成文档结构
    outline = create_outline()
    # 步骤4: 撰写内容
    content = write_content(outline, research)
    return content"""

        # 5. 守卫约束生成
        guards = ["遵循任务原始意图", "输出格式严格符合要求"]
        if self.ollama and self.ollama.available:
            prompt = f"""任务类型：{task_type}
任务描述：{nl_input}
请生成 2-3 条合理的约束条件（守卫），确保 AI 不偏离意图，例如“不得泄露敏感信息”、“必须包含错误处理”等。以 JSON 列表形式返回，例如 ["约束1", "约束2"]。只返回 JSON。"""
            extra_guards = self.ollama.generate_json(prompt)
            if isinstance(extra_guards, list):
                guards.extend(extra_guards)

        # 6. 组装 SPL
        meta = {
            "role": role,
            "style": "Professional",
            "techniques": techniques,
            "task_type": task_type
        }
        interface = {
            "input": input_fields,
            "output": {"format": output_format}
        }
        spl_dict = {
            "@meta": meta,
            "@interface": interface,
            "@protocol": protocol_code.strip(),
            "@guards": guards
        }

        return yaml.dump(spl_dict, allow_unicode=True, sort_keys=False, indent=2)

# ================== Main Compiler ==================
class SPLCompiler:
    def __init__(self, use_ollama=True, model="qwen3.5:9b", debug=False, timeout=60):
        self.ollama = None
        if use_ollama:
            self.ollama = OllamaClient(model=model, debug=debug, timeout=timeout)
            if not self.ollama.available:
                print("[编译器] Ollama 服务不可用，将使用规则模式（自动补全功能受限）")
                self.ollama = None
        self.matcher = TechniqueMatcher()
        self.classifier = TaskClassifier(self.ollama)
        self.detector = GapDetector(self.ollama)
        self.prompter = InteractivePrompter()
        self.generator = SPLGenerator(self.ollama)

    def compile(self, nl_input: str) -> str:
        print(f"[编译器] 分析意图中...")
        techniques = self.matcher.match(nl_input)
        print(f"[编译器] 匹配技巧: {techniques}")

        print(f"[编译器] 识别任务类型...")
        task_type = self.classifier.classify(nl_input)
        print(f"[编译器] 任务类型: {task_type}")

        gaps = self.detector.detect(nl_input, techniques)
        if gaps:
            print(f"[编译器] 检测到 {len(gaps)} 项信息缺失，需要您补充：")
            answers = self.prompter.ask(gaps)
        else:
            answers = {}

        print(f"[编译器] 生成 SPL 代码...")
        spl = self.generator.generate(nl_input, techniques, answers, task_type)
        return spl

def main():
    print("=== SPL 编译器 v2.3（简洁协议版）===")
    print("输入您的任务描述（支持多行，空行结束）：")
    lines = []
    while True:
        line = input()
        if line == "":
            break
        lines.append(line)
    nl_input = "\n".join(lines)

    # 可调整参数
    use_ollama = True
    model = "qwen3.5:9b"
    debug = True          # 开启调试输出
    timeout = 60          # 超时时间

    compiler = SPLCompiler(use_ollama=use_ollama, model=model, debug=debug, timeout=timeout)
    spl_output = compiler.compile(nl_input)

    print("\n" + "="*50)
    print("生成的 SPL 语言：")
    print(spl_output)

    save = input("\n是否保存到文件？(y/n): ").strip().lower()
    if save == 'y':
        filename = input("文件名（默认 output.spl）: ").strip() or "output.spl"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(spl_output)
        print(f"已保存到 {filename}")

if __name__ == "__main__":
    main()