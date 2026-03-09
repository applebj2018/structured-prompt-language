# SPL (Structured Prompt Language) 编译器

## 项目简介

SPL（Structured Prompt Language）是一种介于自然语言和编程语言之间的结构化描述语言，用于精确表达对大语言模型（LLM）的指令。本项目实现了 SPL 语言的编译器，可以将自然语言描述自动转换为结构化的 SPL 代码。

**设计目标**  
- **精确性**：消除自然语言的歧义，明确输入输出格式和逻辑约束。  
- **结构化**：像编程一样组织提示词，便于复用和版本控制。  
- **可读性**：程序员熟悉的结构，降低阅读成本。  
- **可扩展性**：支持自定义技巧、角色和约束。  
- **模型友好**：LLM 在训练中大量接触代码和结构化数据，能更准确地理解 SPL。

---

## SPL 语言语法规范

SPL 文件采用 YAML 格式，包含五个主要部分：`@meta`、`@interface`、`@protocol`、`@guards` 和可选的 `@examples`。

### 1. `@meta` - 元数据

定义任务的全局属性。

| 字段       | 类型   | 必填 | 说明 |
|-----------|--------|------|------|
| `role`    | string | 是   | 执行任务的角色描述 |
| `style`   | string | 否   | 语气风格，如"Professional"、"Friendly" |
| `techniques` | list | 否   | 使用的提示技巧列表 |
| `task_type` | string | 否   | 任务类型（编程、写作、分析等） |

**示例：**
```yaml
@meta:
  role: "资深安全工程师，熟悉 OWASP Top 10"
  style: "Professional"
  techniques: ["步骤清晰", "原因解释"]
```

### 2. `@interface` - 接口定义

明确定义输入和输出的格式，类似函数签名。

**支持的数据类型：**
- `String`：字符串
- `Integer`：整数
- `Float`：浮点数
- `Boolean`：布尔值
- `List`：列表，可指定元素类型，如 `List[String]`
- `JSON`：任意 JSON 对象
- `Image`：图像路径或 base64
- `File`：文件路径

**示例：**
```yaml
@interface:
  input:
    code: String
    language: String
    strict_mode: Boolean
  output:
    format: "JSON"
    schema:
      fields: ["issues", "risk_score"]
```

### 3. `@protocol` - 逻辑协议

用 Python 风格的伪代码描述任务的核心执行步骤。

- 使用 `def` 定义主函数
- 支持 `if/elif/else`、`for/foreach`、`while`、`try/except`、`return`
- 可使用自然语言注释说明步骤

**示例：**
```python
@protocol:
  def process(input):
      # 解析代码
      ast = parse(input.code, input.language)
      # 检测漏洞
      vulnerabilities = scan(ast)
      if vulnerabilities:
          for v in vulnerabilities:
              v.fix = generate_fix(v)
          return {"status": "vulnerable", "list": vulnerabilities}
      else:
          return {"status": "clean"}
```

### 4. `@guards` - 守卫约束

定义必须遵守的规则或禁止事项，以列表形式给出。

**示例：**
```yaml
@guards:
  - "不得泄露任何敏感信息"
  - "输出必须严格符合 JSON 格式"
  - "如果输入代码为空，返回错误码 400"
```

### 5. `@examples` - 示例（可选）

提供少量输入输出示例，用于 few-shot 引导。

**示例：**
```yaml
@examples:
  - in: "print('hello')"
    out: {"issues": [], "risk_score": 0}
  - in: "eval(request.GET['code'])"
    out: {"issues": ["code injection"], "risk_score": 9}
```

---

## 完整示例

### 示例 1：代码安全审查

```yaml
@meta:
  role: "资深安全工程师，5 年渗透测试经验"
  style: "Professional"
  techniques: ["步骤清晰", "原因解释"]

@interface:
  input:
    code: String
    language: String
  output:
    format: "JSON"

@protocol:
  def analyze_security(input):
      ast = parse_ast(input.code, input.language)
      issues = []
      foreach node in ast:
          if is_sql_injection_risk(node):
              issues.append({
                  "type": "SQL Injection",
                  "line": node.line,
                  "risk": "high"
              })
          elif is_xss_risk(node):
              issues.append({
                  "type": "XSS",
                  "line": node.line,
                  "risk": "medium"
              })
      if issues:
          return {"issues": issues, "summary": f"Found {len(issues)} issues"}
      else:
          return {"issues": [], "summary": "No vulnerabilities detected"}

@guards:
  - "不要给出虚假的漏洞报告"
  - "输出必须包含 risk 字段"
```

### 示例 2：财务报告分析

```yaml
@meta:
  role: "财务分析师，擅长解读财报"
  style: "Concise"
  techniques: ["目标驱动", "明确输出格式"]

@interface:
  input:
    report_text: String
    year: Integer
  output:
    format: "Markdown"

@protocol:
  def analyze_financials(input):
      # 提取关键指标
      revenue = extract(input.report_text, "总收入")
      profit = extract(input.report_text, "净利润")
      debt = extract(input.report_text, "总负债")
      
      # 计算比率
      profit_margin = profit / revenue
      debt_ratio = debt / revenue
      
      # 生成结论
      if profit_margin > 0.2:
          conclusion = "盈利能力强劲"
      elif profit_margin > 0.1:
          conclusion = "盈利能力一般"
      else:
          conclusion = "盈利能力较弱"
      
      return f"""
# {input.year}年财务分析

- 总收入：{revenue}
- 净利润：{profit}
- 利润率：{profit_margin:.2%}
- 负债率：{debt_ratio:.2%}

**结论**：{conclusion}
"""

@guards:
  - "只基于提供的数据分析，不臆测"
  - "保留两位小数"
```

---

## spl.py 程序功能说明

### 概述

`spl.py` 是 SPL 编译器的核心实现，它通过本地运行的 Ollama 大模型（默认使用 `qwen3.5:9b`）将用户的自然语言描述智能转换为结构化的 SPL 代码。

### 核心模块

#### 1. **OllamaClient** - Ollama 客户端
负责与本地 Ollama 服务通信，调用大模型进行文本生成和 JSON 格式输出。

**主要方法：**
- `generate(prompt, system_prompt)`：调用 Ollama 生成文本
- `generate_json(prompt, system_prompt)`：要求模型返回 JSON 格式

#### 2. **TechniqueMatcher** - 技巧匹配器
基于关键词匹配自动识别用户描述中隐含的提示技巧。

**支持的技巧类型：**
- 角色扮演、步骤清晰、限定条件、原因解释
- 伪代码、目标驱动、明确输出格式
- 让 AI 提问、输出细致程度、压缩/总结
- 查询最新技术、性格特点、格式化提示词
- 分段专注、合并、排除不可行方案
- 个性喜好、让 AI 给例子、先生成提示词、外部工具

**工作原理：**
通过预定义的关键词映射表，检测用户输入中包含的关键词，自动匹配相应的提示技巧。

#### 3. **TaskClassifier** - 任务分类器
识别用户任务的类型，用于自动补全角色上下文。

**支持的任务类型：**
- 编程、写作、分析、设计、问答、通用

**分类方式：**
1. 优先使用 Ollama 模型进行智能分类
2. 降级到基于关键词的快速分类（备选方案）

#### 4. **GapDetector** - 缺失信息检测器
检测用户描述中缺失的关键信息，并使用大模型生成建议。

**主要功能：**
- 规则检测：检查是否缺少角色、输出格式等必要信息
- 智能补全：根据任务类型自动生成丰富的角色描述

**示例：**
```python
detector.suggest_role_context("编程", "帮我检查代码")
# 输出："资深软件工程师，5 年以上开发经验，熟悉系统架构和代码优化"
```

#### 5. **InteractivePrompter** - 交互式问答器
当检测到信息缺失时，向用户提问以补充必要的上下文信息。

**工作流程：**
1. 遍历所有检测到的缺失项
2. 逐个向用户提问
3. 收集并存储用户回答

#### 6. **SPLGenerator** - SPL 生成器
核心生成模块，使用大模型丰富 SPL 的各个组成部分。

**生成流程：**
1. **角色构建**：优先使用用户回答的角色，否则由模型自动生成
2. **输出格式**：从用户回答中提取，或使用默认值
3. **输入接口推断**：使用模型推断任务需要的输入参数
4. **协议伪代码生成**：将任务描述转化为结构化的伪代码步骤
5. **守卫约束生成**：生成 2-3 条合理的约束条件
6. **组装 SPL**：将所有部分组合成 YAML 格式

#### 7. **SPLCompiler** - 主编译器
整合所有模块，提供完整的编译流程。

**编译流程：**
```
用户输入 → 意图分析 → 技巧匹配 → 任务分类 
        → 缺失检测 → 交互问答 → SPL 生成 → 输出
```

### 使用方法

#### 直接运行
```bash
python spl.py
```

#### 交互式使用示例
```
=== SPL 编译器 v2.0（自动补全上下文）===
输入您的任务描述（支持多行，空行结束）：
帮我分析一段 Python 代码，检查是否有内存泄漏，输出 Markdown 格式。

[编译器] 分析意图中...
[编译器] 匹配技巧：['步骤清晰', '明确输出格式', '目标驱动']
[编译器] 识别任务类型：编程
[编译器] 检测到 1 项信息缺失，需要您补充：
[编译器] 您希望设定什么角色来处理这个任务？
[用户] 资深 Python 工程师，5 年以上性能优化经验
[编译器] 生成 SPL 代码...

==================================================
生成的 SPL 语言：
@meta:
  role: 资深 Python 工程师，5 年以上性能优化经验
  style: Professional
  techniques:
  - 步骤清晰
  - 明确输出格式
  - 目标驱动
  task_type: 编程
@interface:
  input:
    code: String
  output:
    format: MARKDOWN
@protocol: |
  def analyze_memory(code):
      # 解析代码
      ast = parse_ast(code)
      # 检测内存泄漏模式
      leaks = detect_leaks(ast)
      if leaks:
          suggestions = generate_fixes(leaks)
      else:
          suggestions = "未检测到内存泄漏"
      return suggestions
@guards:
- 遵循任务原始意图
- 输出格式严格符合要求
- 不得泄露敏感信息

是否保存到文件？(y/n): y
文件名（默认 output.spl）: code_review.spl
已保存到 code_review.spl
```

### 依赖安装

```bash
pip install requests pyyaml
```

### 环境要求

- **Python**: 3.7+
- **Ollama**: 需要本地安装并运行 Ollama 服务
- **模型**: 默认使用 `qwen3.5:9b`，可通过修改 `model` 参数切换

**安装 Ollama：**
```bash
# Linux/macOS
curl -fsSL https://ollama.com/install.sh | sh

# 启动服务
ollama serve

# 拉取模型
ollama pull qwen3.5:9b
```

### 配置选项

在 `SPLCompiler` 初始化时可以配置：

```python
# 使用 Ollama（推荐）
compiler = SPLCompiler(use_ollama=True, model="qwen3.5:9b")

# 不使用 Ollama（仅使用规则匹配）
compiler = SPLCompiler(use_ollama=False)
```

---

## 最佳实践

1. **角色具体化**：角色描述越具体，模型越能聚焦领域知识。
2. **接口清晰化**：明确输入输出的类型和结构，避免模糊。
3. **协议结构化**：用伪代码分步描述逻辑，便于模型遵循。
4. **守卫精炼化**：添加关键约束，防止模型产生意外行为。
5. **示例引导**：对于复杂任务，提供少量示例可显著提升准确性。
6. **版本控制**：将 .spl 文件纳入 Git 管理，记录提示词变更。
7. **测试迭代**：用不同输入测试 SPL 的效果，不断优化。

---

## 与普通提示词对比

| 特性 | 自然语言提示词 | SPL |
|------|---------------|-----|
| 精确性 | 模糊，易歧义 | 结构化，类型明确 |
| 可读性 | 依赖写作水平 | 统一格式，程序员友好 |
| 可维护性 | 难以复用 | 可模块化、版本控制 |
| 模型遵循度 | 中等 | 高（激活代码思维） |
| 自动化支持 | 低 | 高（可编译生成） |

---

## 扩展性

SPL 可以扩展自定义字段和技巧。例如：
- 增加 `@tools` 部分声明外部工具调用
- 增加 `@workflow` 定义多步任务
- 社区可以贡献更多技巧触发器，丰富编译器逻辑

---

## 故障排除

### 常见问题

**1. Ollama 连接失败**
```
[Ollama Error] HTTPConnectionPool(host='localhost', port=11434)
```
**解决：** 确保 Ollama 服务正在运行：`ollama serve`

**2. 模型未找到**
```
Error: model 'qwen3.5:9b' not found
```
**解决：** 拉取模型：`ollama pull qwen3.5:9b`

**3. 生成的 SPL 格式不正确**
- 检查 YAML 缩进是否正确
- 确保特殊字符已正确转义

---

## 许可证

本项目采用开源许可证，欢迎贡献和使用。

---

## 联系方式

如有问题或建议，欢迎提交 Issue。

---

**文档版本**：v2.0  
**最后更新**：2026 年 3 月 9 日  
**作者**：SPL 设计团队
