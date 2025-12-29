---
name: translate-comments-to-chinese
overview: 将项目中所有 Python 文件的注释和文档字符串翻译成中文。
todos:
  - id: scan-python-files
    content: 使用 [subagent:code-explorer] 扫描并识别项目中所有 Python 文件
    status: completed
  - id: translate-models
    content: 翻译 models 模块中的所有注释和文档字符串
    status: completed
    dependencies:
      - scan-python-files
  - id: translate-websocket
    content: 翻译 websocket 模块中的所有注释和文档字符串
    status: completed
    dependencies:
      - scan-python-files
  - id: translate-analyzers
    content: 翻译 analyzers 模块中的所有注释和文档字符串
    status: completed
    dependencies:
      - scan-python-files
  - id: translate-detectors
    content: 翻译 detectors 模块中的所有注释和文档字符串
    status: completed
    dependencies:
      - scan-python-files
  - id: translate-pool-manager
    content: 翻译 pool_manager 模块中的所有注释和文档字符串
    status: completed
    dependencies:
      - scan-python-files
  - id: translate-orchestrator
    content: 翻译 orchestrator 模块中的所有注释和文档字符串
    status: completed
    dependencies:
      - scan-python-files
---

## 产品概述

对 arbitrage-mvp 项目进行代码注释本地化，将所有 Python 文件中的英文注释和文档字符串翻译成中文，提高代码的可读性和维护性。

## 核心功能

- 扫描项目中所有 Python 文件
- 识别单行注释（#）和多行文档字符串（""" 或 '''）
- 将英文注释内容准确翻译成中文
- 保持代码逻辑和结构完全不变
- 保留代码中的技术术语和变量名不变

## 技术栈

- 项目类型：Python 代码国际化（i18n）
- 文件处理：Python 内置文件操作
- 扫描工具：使用 code-explorer 扩展进行代码探索

## 技术架构

### 系统架构

```mermaid
graph LR
    A[扫描项目目录] --> B[识别Python文件]
    B --> C[提取注释和文档字符串]
    C --> D[翻译英文内容]
    D --> E[更新文件内容]
    E --> F[验证代码完整性]
```

### 模块划分

- **扫描模块**：遍历项目目录，识别所有 .py 文件
- **解析模块**：提取代码中的注释和文档字符串
- **翻译模块**：将英文注释翻译成中文
- **更新模块**：将翻译后的内容写回文件

### 数据流

项目扫描 → Python文件列表 → 提取注释内容 → 翻译处理 → 替换原注释 → 写入文件

## 实现细节

### 核心目录结构

```
e:/project/ai/arbitrage-mvp/
├── models/                  # 数据模型模块
├── websocket/               # WebSocket 客户端
├── analyzers/               # 价格分析器
├── detectors/               # 套利检测器
├── pool_manager/            # 池子管理器
└── orchestrator/            # 主程序编排器
```

### 关键代码结构

- **注释识别模式**：正则表达式匹配 `#.* 和 `(\"\"\"|\'\'\').*?(\"\"\"|\'\'\')`
- **翻译策略**：保持代码逻辑不变，仅翻译注释内容
- **文件更新流程**：读取 → 修改 → 写入（原子操作）

## Agent Extensions

### SubAgent

- **code-explorer**
- 用途：搜索和遍历项目中的所有 Python 文件
- 预期结果：获取完整的 Python 文件列表及其路径，以便逐一处理