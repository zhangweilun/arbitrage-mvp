---
name: fix-config-indentation
overview: 修复 config.py 中多个 property 方法的 docstring 缩进错误
todos:
  - id: fix-indentation
    content: 修复 config.py 中 @property 方法的 docstring 缩进错误
    status: completed
---

## 产品概述

修复 config.py 文件中多个 @property 方法的 docstring 缩进错误

## 核心功能

- 修正第 65 行开始的 @property 方法 docstring 缩进
- 将错误的 12 个空格缩进调整为正确的 8 个空格
- 确保修复后代码不产生 IndentationError

## 技术栈

- 项目类型：Python 现有项目修改
- 修改文件：config.py

## 架构设计

### 修改范围

- 仅涉及 config.py 文件中 docstring 缩进问题
- 保持现有代码逻辑和架构不变

### 修改细节

- 目标行：从第 65 行开始的 @property 方法
- 修改内容：将 docstring 缩进从 12 空格减少到 8 空格
- 验证方式：运行 Python 语法检查确保无 IndentationError