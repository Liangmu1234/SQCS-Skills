---
name: ts-knowledge-base
description: H3C 售前测试知识库查询助手。用于在 H3C 内部知识库中检索产品信息、测试文档、技术规范等。触发条件：(1) 用户询问 H3C 服务器产品参数、规格、型号；(2) 需要查询售前测试相关文档和规范；(3) 询问 benchmark 测试方法、服务器配置、固件升级等技术支持问题；(4) 用户要求"查一下知识库"、"搜索文档"、"找一下XXX资料"。用户账号 z62875，通过 deepsearch streamv1 接口查询，关联知识库 source：www,pmo,cjg,cmp,press,wwwen,ts_sqcs_knowleged。
---

# H3C 知识库查询技能

## 接口信息

- **接口地址**：POST https://api-ai.h3c.com/deepsearch/api-search/v1/streamv1
- **用户账号**：z62875（作为 user_id 参数）
- **关联知识库**：www,pmo,cjg,cmp,press,wwwen,ts_sqcs_knowleged
- **返回格式**：SSE 流式响应，需要收集 Final Answer / Outline Answer 类型的 chunk
- **无需 token**：此接口不需要登录认证，直接使用 user_id: z62875 即可

## 使用方式

### 通过 Node.js 脚本查询（推荐）

`ash
node scripts/query.js "R4900 G7 服务器参数"
node scripts/query.js "NVMe 测试方法" --deep
`

### 参数说明

| 参数 | 说明 |
|------|------|
| 	ask | 用户问题（必填）|
| source | 知识库来源，多个用逗号分隔 |
| user_id | 用户账号，固定为 z62875 |
| session_id | 会话ID，UUID 格式 |
| pplication | 应用名，固定为 zhidao |
| searchonly | 是否只搜索，默认 false |
| outline | 是否生成大纲，默认 false |

## 典型查询场景

- 产品规格对比（"R4900 G6 和 R5500 G7 有什么区别"）
- 测试方法查询（"如何测试 NVMe 盘性能"）
- 固件升级指导（"R5300 G7 固件升级步骤"）
- Benchmark 工具使用（"stream 测试怎么跑"）
- 服务规范查询（"售前测试流程是什么"）