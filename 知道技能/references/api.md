# H3C 知识库 API 参考

## 查询接口（deepsearch streamv1）

**接口地址**：POST https://api-ai.h3c.com/deepsearch/api-search/v1/streamv1

**请求体**：
`json
{
  "task": "R4900 G7 服务器参数",
  "source": "www,pmo,cjg,cmp,press,wwwen,ts_sqcs_knowleged",
  "user_id": "z62875",
  "session_id": "uuid-格式的会话ID",
  "application": "zhidao",
  "searchonly": false,
  "outline": false
}
`

**响应格式**：SSE 流式，每条消息格式：
`
data: {"code":200,"msg":"success","data":{"content":"内容","role":"assistant","metadata":{"title":"Final Answer"}}}
`

**关键 metadata.title 值**：
- Step - 思考步骤编号
- Model output - 模型思考输出（逐字返回）
- Final Answer - 最终答案（逐字返回，需拼接）
- Reference information - 参考资料列表（content_type=list 时解析为 JSON 数组）
- Stream End - 流结束标记

**注意**：Model output 和 Final Answer 都是逐字返回的 SSE chunk，需要全部拼接才是完整内容。

## 登录接口（不适用于此场景）

POST https://api-ai.h3c.com/session/api/user/login

此接口需要特定的前置认证，当前无法直接调用。查询接口本身不需要 token。

## source 可选值

| source | 说明 |
|--------|------|
| www | H3C 官网 |
| pmo | PMO |
| cjg | 产品中心 |
| cmp | CMP |
| press | 新闻稿 |
| wwwen | 英文官网 |
| ts_sqcs_knowleged | 售前测试知识库 |