# Model Notes

Use these only when the named model matches.

## GLM-4.6V On yez

Known-good target:

- Host: `10.12.180.20`
- Path: `/home/data/GLM-4.6V`
- Served name: `GLM-4.6V`
- Port: `8003`
- Backend: host `vllm 0.17.1`
- Context policy: default; logs resolve `Using max model len 131072`
- Parallelism: `--tensor-parallel-size 4 --pipeline-parallel-size 2`

Compatibility notes:

- The old container image `gpuh20_sqcs_aik:1` had `vLLM 0.7.3` and did not recognize `glm4v_moe`; host vLLM worked.
- `transformers 4.56.0` made `AutoProcessor` return `PreTrainedTokenizerFast`; upgrading to `transformers==5.10.2` made it return `Glm46VProcessor`.
- Public PyPI was slow; use `https://pypi.tuna.tsinghua.edu.cn/simple` if needed.

Known-good command:

```bash
nohup vllm serve /home/data/GLM-4.6V \
  --api-key "$API_KEY" \
  --served-model-name GLM-4.6V \
  --host 0.0.0.0 \
  --port 8003 \
  --trust-remote-code \
  --tensor-parallel-size 4 \
  --pipeline-parallel-size 2 \
  --gpu-memory-utilization 0.95 \
  --enable-chunked-prefill \
  --enable-auto-tool-choice \
  --tool-call-parser glm45 \
  --reasoning-parser glm45 \
  --limit-mm-per-prompt '{"image": 8}' \
  --max-num-seqs 16 \
  > /home/vllm_glm4_6v_codex.log 2>&1 &
```

Do not add `--max-model-len` when default context is requested.
