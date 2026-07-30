---
name: model-interface
description: Use when asked to connect to a server and start, inspect, validate, or document a standard model inference service, especially OpenAI-compatible vLLM endpoints for local model directories.
---

# Model Interface

## Purpose

Use this skill to turn a local model directory into a working inference endpoint. The default target is an OpenAI-compatible vLLM service, but the workflow is deliberately model-agnostic: discover the model, inspect existing scripts, choose safe runtime parameters, start the service, validate it, and return the URL/model/API key.

This skill includes the server connection phase. Use the `ssh-content` workflow for SSH mechanics, credentials hygiene, remote command execution, and GPU/kernel recovery before doing model-specific work.

## Inputs To Establish

Infer these from the user's request and server state; ask only when missing and risky:

- target server, defaulting to `10.12.180.20` if the conversation is about `yez`;
- model path, commonly under `/home/data/<model-name>`;
- served model name, defaulting to the directory basename;
- port, defaulting to an unused OpenAI port such as `8003`;
- backend, defaulting to `vllm serve` when available;
- API key, generating a fresh one unless the user supplies one;
- context length policy. If the user says "default context", do not pass `--max-model-len`.

## Discovery

Connect using `ssh-content`, then inspect the server before starting anything:

```bash
hostname
uname -r
nvidia-smi
systemctl is-active nvidia-fabricmanager 2>/dev/null || true
find /home/data -maxdepth 1 -mindepth 1 -type d -printf '%TY-%Tm-%Td %TH:%TM %f\n' 2>/dev/null | sort
find /home -maxdepth 2 -type f \( -name '*.sh' -o -name '*vllm*' -o -name '*sglang*' -o -name '*serve*' \) -printf '%TY-%Tm-%Td %TH:%TM %p\n' 2>/dev/null | sort
docker ps -a --format 'table {{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}\t{{.Names}}' 2>/dev/null || true
ss -tlpen 2>/dev/null | grep -E ':(8000|8001|8002|8003|8080)\b' || true
```

Read relevant existing scripts before inventing new parameters:

```bash
sed -n '1,220p' /home/<candidate-script>.sh
```

Prefer the existing local pattern when it is compatible with the requested model and current software versions.

## Runtime Checks

Verify the backend and model support:

```bash
which vllm || true
vllm --version 2>&1 || true
python3 - <<'PY'
import torch
print("torch", torch.__version__, "cuda", torch.version.cuda, "available", torch.cuda.is_available(), "count", torch.cuda.device_count())
PY
test -d "$MODEL_PATH" && ls -ld "$MODEL_PATH"
sed -n '1,120p' "$MODEL_PATH/config.json" 2>/dev/null || true
```

If the model is multimodal or newly released, check processor support:

```bash
python3 - <<'PY'
import os, transformers
from transformers import AutoConfig, AutoProcessor
model = os.environ["MODEL_PATH"]
print("transformers", transformers.__version__)
cfg = AutoConfig.from_pretrained(model, trust_remote_code=True)
print("model_type", getattr(cfg, "model_type", None))
try:
    p = AutoProcessor.from_pretrained(model, trust_remote_code=True)
    print("processor", type(p))
except Exception as e:
    print("processor_error", type(e).__name__, e)
PY
```

When a model requires a newer dependency, prefer the least invasive targeted upgrade and use a domestic mirror if public PyPI is slow:

```bash
python3 -m pip install --upgrade --default-timeout 300 --retries 5 --progress-bar off \
  -i https://pypi.tuna.tsinghua.edu.cn/simple '<package>==<version>'
```

## Choosing Parameters

Start from a conservative vLLM command:

- `--host 0.0.0.0`
- `--port <PORT>`
- `--served-model-name <MODEL_NAME>`
- `--api-key <API_KEY>`
- `--trust-remote-code` for local/community models that need custom code
- `--tensor-parallel-size` matching the intended GPU shard count
- `--pipeline-parallel-size` only when existing scripts or model size require it
- `--gpu-memory-utilization` near existing known-good values, commonly `0.90` to `0.95`
- `--enable-chunked-prefill` for long-context models when supported
- multimodal limits such as `--limit-mm-per-prompt` only when the backend/version supports the syntax

Do not set `--max-model-len` when the user wants the model default. Confirm the resolved context in logs.

Model-specific notes, including the GLM-4.6V known-good command and compatibility pitfall, live in `references/model-notes.md`; read it when working with a named model from that file.

## Start Pattern

Use a per-model script and log. Avoid hard-coded model names in the skill; substitute values from discovery.

```bash
MODEL_PATH="/home/data/<model-dir>"
MODEL_NAME="<served-name>"
PORT="8003"
API_KEY="sk-${MODEL_NAME//[^A-Za-z0-9]/-}-$(openssl rand -hex 16)"
SAFE_NAME="$(echo "$MODEL_NAME" | tr -c 'A-Za-z0-9_.-' '_' | tr '[:upper:]' '[:lower:]')"
LOG="/home/vllm_${SAFE_NAME}.log"
SCRIPT="/home/vllm_load_${SAFE_NAME}.sh"

pkill -f "vllm serve $MODEL_PATH" 2>/dev/null || true

cat > "$SCRIPT" <<EOF
#!/usr/bin/env bash
export VLLM_LOGGING_LEVEL=INFO
export SAFETENSORS_FAST_GPU=1
export CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7
export OMP_NUM_THREADS=8
export CUDA_DEVICE_MAX_CONNECTIONS=1
cd /home
nohup vllm serve "$MODEL_PATH" \\
  --api-key "$API_KEY" \\
  --served-model-name "$MODEL_NAME" \\
  --host 0.0.0.0 \\
  --port "$PORT" \\
  --trust-remote-code \\
  --tensor-parallel-size 8 \\
  --gpu-memory-utilization 0.90 \\
  --enable-chunked-prefill \\
  > "$LOG" 2>&1 &
echo \$! > "\${LOG%.log}.pid"
EOF
chmod +x "$SCRIPT"
"$SCRIPT"
```

Adjust parallelism and model-specific flags based on existing scripts, GPU memory, and `vllm serve --help`. If a container is requested, first verify the container can see GPUs and has a compatible backend version; do not assume an old image supports new model architectures.

## Readiness And Validation

Wait for the service to listen:

```bash
tail -n 120 "$LOG"
ss -tlpen 2>/dev/null | grep ":$PORT"
nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader,nounits
```

Expected vLLM signals include resolved architecture, resolved max model length, checkpoint loading, KV cache initialization, and the port listening.

Validate from the server:

```bash
curl -sS -H "Authorization: Bearer $API_KEY" "http://127.0.0.1:$PORT/v1/models"
curl -sS -H "Authorization: Bearer $API_KEY" -H 'Content-Type: application/json' \
  "http://127.0.0.1:$PORT/v1/chat/completions" \
  -d "{\"model\":\"$MODEL_NAME\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply in one short sentence: what model are you?\"}],\"max_tokens\":80,\"temperature\":0}"
```

If server-local validation succeeds but workstation access times out, report that the inference service is healthy locally and separately check routing/firewall/listener exposure.

## Return To User

Return:

```text
Base URL: http://<host>:<port>/v1
Model: <served model name>
API Key: <generated or supplied key>
```

Include a concise OpenAI-compatible `curl` or Python example. Mention whether the context length was default or explicitly set, and cite the resolved value when logs show it.
