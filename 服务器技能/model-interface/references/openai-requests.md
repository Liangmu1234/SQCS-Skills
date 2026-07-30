# OpenAI-Compatible Requests

Replace placeholders before returning examples:

- `BASE_URL`, for example `http://10.12.180.20:8003/v1`
- `API_KEY`
- `MODEL_NAME`

## List Models

```bash
curl BASE_URL/models \
  -H "Authorization: Bearer API_KEY"
```

## Chat Completion

```bash
curl BASE_URL/chat/completions \
  -H "Authorization: Bearer API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "MODEL_NAME",
    "messages": [
      {"role": "user", "content": "Reply in one short sentence: what model are you?"}
    ],
    "max_tokens": 80,
    "temperature": 0
  }'
```

## Python Client

```python
from openai import OpenAI

client = OpenAI(
    base_url="BASE_URL",
    api_key="API_KEY",
)

resp = client.chat.completions.create(
    model="MODEL_NAME",
    messages=[{"role": "user", "content": "Reply in one short sentence: what model are you?"}],
    max_tokens=80,
    temperature=0,
)
print(resp.choices[0].message.content)
```
