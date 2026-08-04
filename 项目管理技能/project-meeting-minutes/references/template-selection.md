# 会议纪要模板选择

模板仓库：[Liangmu1234/Meeting-Minutes-Template](https://github.com/Liangmu1234/Meeting-Minutes-Template)（`main` 分支）。

先通过 `scripts/prepare_project_minutes.ps1` 将仓库浅克隆或刷新到 `%LOCALAPPDATA%\Codex\Meeting-Minutes-Template`。模板文件和 `00-[项目模板-XX年XX月]` 项目目录模板均从该受控缓存读取；远端历史重写时使用带提交号后缀的新快照，不得修改任何缓存中的源文件。

同步后检查仓库根目录中的实际文件；下表仅用于语义匹配，文件不存在时不得虚构路径。

| 会议主题或产品 | 首选模板 |
|---|---|
| GPU、DCU、NPU、AI加速卡、异构算力服务器、训练/推理卡测试 | `异构服务器.xlsx` |
| 智算中心总体方案、算力中心建设、集群级智算方案 | `智算中心解决方案.xlsx` |
| AIGC应用、大模型应用方案、生成式AI方案 | `AIGC解决方案 .xlsx` |
| 国产CPU服务器、国产化通用服务器 | `国产服务器.xlsx` |
| x86通用服务器、非HPE商用服务器 | `商用服务器.xlsx` |
| HPE服务器 | `HPE服务器.xlsx` |
| 存储系统 | `存储.xlsx` |
| 备份、容灾备份 | `备份.xlsx` |
| 路由器、交换机、园区/数据中心基础网络 | `路由交换.xlsx` |
| 无线网络、AP、AC | `无线.xlsx` |
| 无损网络、RoCE、智算网络 | `SeerFabric无损网络解决方案.xlsx` |
| SD-WAN | `SD-WAN .xlsx` |
| AD-WAN、AD-DC、网流、AD-campus | 对应名称模板 |
| 防火墙、应用交付 | `防火墙&应用交付.xlsx` |
| 零信任 | `零信任.xlsx` |
| 云安全 | `云安全.xlsx` |
| 态势感知 | `态势感知系列.xlsx` |
| CAS、UIS、虚拟化 | `CAS&UIS.xlsx` |
| CloudOS、云平台 | `CloudOS.xlsx` |
| iMC、准入控制 | `iMC&准入.xlsx` |
| U-Center、统一运维管理 | `U-center.xlsx` |
| 灵犀使能平台 | `灵犀使能平台.xlsx` |
| 大数据平台 | `大数据.xlsx` |
| 产品合作、联合方案且无法归入具体产品线 | `产品合作类.xlsx` |

## 选择规则

1. 以本次被测对象为主，不只看客户行业或会议中出现频率最高的词。
2. 同时涉及多产品时，优先选择承担主要测试责任、占测试范围最大的产品模板。
3. “服务器+加速卡”优先选异构服务器；“完整智算中心集群建设”优先选智算中心解决方案。
4. 模板名称与主题无法形成高置信匹配时，列出最接近的两个模板并请用户选择。
5. 选择后使用 `-MinutesTemplateName <模板文件名>` 从仓库缓存复制到项目的 `8.其他`，再读取和填写副本。
