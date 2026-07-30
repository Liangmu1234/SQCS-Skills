# academic-image-to-vba skill

A Codex/agent skill for converting reference images into hybrid editable PPTX + Office VBA reconstruction code.

## Install

Copy this folder to one of these locations:

```text
<project>/.agents/skills/academic-image-to-vba
$HOME/.agents/skills/academic-image-to-vba
```

Then invoke it in Codex with:

```text
$academic-image-to-vba 把这张PPT图片转成混合可编辑版：文字/形状可编辑，复杂图片裁剪插入，同时输出PPTX和VBA宏。
```

## Test scripts

```bash
pip install -r requirements.txt
python scripts/layout_to_vba.py examples/layout_example.json --out /tmp/reconstruction_macro.bas
python scripts/build_pptx.py examples/layout_example.json --out /tmp/reconstructed.pptx
```
