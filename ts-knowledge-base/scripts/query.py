import sys
import json
import uuid
import http.client
import ssl

# ========== 配置 ==========
ACCOUNT = "ts_sqcs_knowleged"
PASSWORD = "TS_sqcs_knowleged_123"
SOURCES = ["www", "pmo", "cjg", "cmp", "press", "wwwen", "ts_sqcs_knowleged"]
BASE_URL = "https://api-searchservice.h3c.com"
TEST_URL = "https://api-searchservice-ts.h3c.com"
USE_TEST = True   # True=测试环境，False=生产环境


def get_host_port():
    url = TEST_URL if USE_TEST else BASE_URL
    host = url.replace("https://", "").split("/")[0]
    return host, 443


def build_payload(task, is_deep_search=False, user_id=None, session_id=None, source=None):
    return json.dumps({
        "isDeepSearch": is_deep_search,
        "task": task,
        "source": ",".join(source or SOURCES),
        "user_id": user_id or ACCOUNT,
        "session_id": session_id or str(uuid.uuid4()),
        "application": "zhidao",
        "searchonly": False
    }, ensure_ascii=False)


def query(question, is_deep_search=False, verbose=False):
    host, port = get_host_port()
    path = /itsearchserve/v1.0/search/getAiResultCommon
    payload = build_payload(question, is_deep_search=is_deep_search).encode("utf-8")

    ctx = ssl.create_default_context()
    conn = http.client.HTTPSConnection(host, port, timeout=60, context=ctx)
    try:
        conn.request("POST", path, body=payload, headers={
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
        resp = conn.getresponse()
        raw = resp.read().decode("utf-8")
    except Exception as e:
        return f"[Error] 连接失败: {e}", []
    finally:
        conn.close()

    try:
        result = json.loads(raw)
    except Exception:
        return f"[Error] 解析响应失败\n原始内容: {raw[:500]}", []

    code = result.get("code", -1)
    if code != 0:
        return f"[Error] code={code}, msg={result.get("msg","")}", []

    data_obj = result.get("data", {})
    answer = data_obj.get("answer", "")
    references = data_obj.get("reference_information", []) or []

    if verbose and references:
        ref_lines = []
        for ref in references:
            title = ref.get("title", "")
            url = ref.get("original_file_path", "")
            ref_lines.append(f"- **{title}** + ("  \n  " + url if url else ""))
        if ref_lines:
            answer += "\n\n---\n**参考资料：**\n" + "\n".join(ref_lines)

    return answer, references


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python query.py <问题> [--deep]")
        sys.exit(1)
    question = sys.argv[1]
    is_deep = "--deep" in sys.argv
    print(f"问题: {question}")
    print(f"深度思考: {is_deep}")
    print(f"URL: {TEST_URL if USE_TEST else BASE_URL}")
    print("---------------")
    answer, refs = query(question, is_deep_search=is_deep, verbose=True)
    print(answer)