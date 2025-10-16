#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Simple test script for SplitMarkdownTreeTool.

It injects lightweight stubs for `myagent` and `fs.memoryfs` so the tool module
can be imported without the full runtime environment. Then it feeds a sample
Markdown string and prints the resulting outline and JSON summary.
"""

from __future__ import annotations

import asyncio
import json
import sys
import types
from pathlib import Path
import importlib.util


def _install_stubs() -> None:
    # Stub for fs.memoryfs.MemoryFS
    fs_mod = types.ModuleType("fs")
    memoryfs_mod = types.ModuleType("fs.memoryfs")

    class MemoryFS:
        def __init__(self):
            self._files = {}
            self._dirs = set(["/"])  # naive dir tracking

        # Minimal methods; not used by this test but keep available
        def exists(self, path: str) -> bool:
            return path in self._files or path in self._dirs

        def isfile(self, path: str) -> bool:
            return path in self._files

        def isdir(self, path: str) -> bool:
            return path in self._dirs

        def listdir(self, path: str):
            return []

        def makedirs(self, path: str, recreate: bool = False):
            self._dirs.add(path)

        def writetext(self, path: str, content: str):
            self._files[path] = content

        def readtext(self, path: str) -> str:
            return self._files[path]

    memoryfs_mod.MemoryFS = MemoryFS
    sys.modules.setdefault("fs", fs_mod)
    sys.modules.setdefault("fs.memoryfs", memoryfs_mod)

    # Stubs for myagent
    myagent_mod = types.ModuleType("myagent")

    class LLM:
        def __init__(self, *_, **__):
            pass

        async def ask(self, *_, **__):
            return "stub"

    myagent_mod.LLM = LLM

    tool_pkg = types.ModuleType("myagent.tool")
    base_tool_mod = types.ModuleType("myagent.tool.base_tool")

    class ToolResult:
        def __init__(self, output=None, error=None, system=None):
            self.output = output
            self.error = error
            self.system = system

    class BaseTool:
        name: str = "base_tool"
        description: str = ""
        parameters = {}

        def __init__(self) -> None:
            pass

    base_tool_mod.ToolResult = ToolResult
    base_tool_mod.BaseTool = BaseTool

    config_mod = types.ModuleType("myagent.config")

    class LLMSettings:
        def __init__(self, model: str, base_url: str | None = None, api_key: str | None = None, max_tokens: int | None = None, temperature: float | None = None):
            self.model = model
            self.base_url = base_url
            self.api_key = api_key
            self.max_tokens = max_tokens
            self.temperature = temperature

    class _Settings:
        class _LLM:
            def __init__(self):
                self.model = "dummy"
                self.base_url = ""
                self.api_key = ""
                self.max_tokens = 2048

        def __init__(self):
            self.llm_settings = self._LLM()

    config_mod.LLMSettings = LLMSettings
    config_mod.settings = _Settings()

    ws_mod = types.ModuleType("myagent.ws")

    def get_ws_session_context():  # noqa: N802
        class _C:
            session_id = "test-session"

        return _C()

    ws_mod.get_ws_session_context = get_ws_session_context

    sys.modules.setdefault("myagent", myagent_mod)
    sys.modules.setdefault("myagent.tool", tool_pkg)
    sys.modules.setdefault("myagent.tool.base_tool", base_tool_mod)
    sys.modules.setdefault("myagent.config", config_mod)
    sys.modules.setdefault("myagent.ws", ws_mod)


def build_sample_markdown() -> str:
    return """
# 企业信贷评估模板

## 一、企业基本信息（必填项）

| 项目 | 内容 | 要求 | 备注 |
|------|------|------|------|
| 企业名称 | [填写完整工商注册名称] | 需与营业执照一致 |  |
| 统一社会信用代码 | [18位代码] | 需通过工商系统验证 |  |
| 成立时间 | [YYYY-MM-DD] | 用于计算经营年限 |  |
| 经营年限 | [ ] 年 | 系统/人工计算 |  |
| 注册资本 | [金额] 万元 | 注明实缴比例 | 实缴比例：[ ]% |
| 法定代表人 | [姓名] | 附身份证号及征信授权 | 身份证号：[ ] |
| 实际控制人 | [姓名/企业名称] | 追溯至最终受益人 | 控制链条说明：[ ] |
| 所属行业 | [选择行业分类] | □ 制造业 □ 服务业 □ 零售业 □ 其他：[ ] | 按内部分类口径 |
| 主营业务 | [简述核心产品/服务，不超过3项] | 聚焦核心 |  |
| 主要业务模式 | [生产/贸易/平台/其他] | 可选 |  |

---

## 二、经营状况分析

总结经营状态（如：持续盈利/亏损，增长/下滑，现金流状况等）：  
[文字描述]

### （一）行业地位评估

1. 市场份额： [ ] % （数据来源： [ ] ）  
2. 竞争优势（勾选或补充）：  
   □ 技术领先	□ 成本优势	□ 品牌优势	□ 渠道优势	□ 政策支持  
3. 行业风险预警（列出 3 项主要风险及应对措施）：

| 序号 | 风险点描述 | 影响说明 | 应对/缓释措施 |
|------|------------|----------|---------------|
| 1 | [ ] | [ ] | [ ] |
| 2 | [ ] | [ ] | [ ] |
| 3 | [ ] | [ ] | [ ] |

### （二）生产经营分析（制造业适用）

| 指标 | 数值 | 行业均值 | 偏离度 | 说明 |
|------|------|----------|--------|------|
| 产能利用率 | [ ] % | [ ] % | [ ] % | 计算口径：[ ] |
| 主要设备成新率 | [ ] % | [ ] % | [ ] % | 设备结构说明：[ ] |
| 原材料自给率 | [ ] % | [ ] % | [ ] % | 关键原料：[ ] |
| 环保达标情况 | □ 达标 □ 整改中 □ 未达标 | -- | -- | 改善计划：[ ] |

### （三）供应链稳定性（零售 / 贸易类适用）

1. 核心供应商（前 3 家及合作年限）：

| 序号 | 供应商名称 | 合作年限(年) | 占采购比重(%) | 依赖风险评估 | 备注 |
|------|------------|--------------|---------------|--------------|------|
| 1 | [ ] | [ ] | [ ] | [低/中/高] | [ ] |
| 2 | [ ] | [ ] | [ ] | [低/中/高] | [ ] |
| 3 | [ ] | [ ] | [ ] | [低/中/高] | [ ] |

2. 采购集中度：CR3 = [ ] %  
3. 应收账款平均账期： [ ] 天  
4. 库存周转天数： [ ] 天（计算说明：[ ]）

---

## 三、财务分析（可对接自动计算）

### （一）偿债能力指标

| 指标 | 计算公式 | 2023年 | 2024年 | 行业标准 | 评价 |
|------|----------|--------|--------|----------|------|
| 流动比率 | \[流动资产 / 流动负债\] | [ ] | [ ] | 1.5–2.0 | [ ] |
| 速动比率 | \[(流动资产 - 存货) / 流动负债\] | [ ] | [ ] | ≥1.0 | [ ] |
| 资产负债率 | \[负债总额 / 资产总额 × 100%\] | [ ] % | [ ] % | ≤60% | [ ] |
| 利息保障倍数 | \[(利润总额 + 财务费用) / 财务费用\] | [ ] | [ ] | ≥3.0 | [ ] |

### （二）盈利能力指标

| 指标 | 计算公式 | 2023年 | 2024年 | 行业标准 | 评价 |
|------|----------|--------|--------|----------|------|
| 销售净利率 | \[净利润 / 营业收入 × 100%\] | [ ] % | [ ] % | ≥[ ] % | [ ] |
| 总资产回报率(ROA) | \[净利润 / 平均总资产 × 100%\] | [ ] % | [ ] % | ≥[ ] % | [ ] |
| 净资产收益率(ROE) | \[净利润 / 平均净资产 × 100%\] | [ ] % | [ ] % | ≥[ ] % | [ ] |

### （三）IFRS 9 预期信用损失（ECL）计算表

| 项目 | 计算过程 | 数值 | 说明 |
|------|----------|------|------|
| 违约概率 (PD) | 内部评级模型 | [ ] % | 模型版本：[ ] |
| 违约损失率 (LGD) | 抵押品类型/回收假设 | [ ] % | 抵押品说明：[ ] |
| 违约风险敞口 (EAD) | 贷款余额 + 未提取承诺 × 承诺使用率 | [ ] | 承诺使用率：[ ] |
| 12个月预期损失 | \[PD × LGD × EAD × (12 / 剩余期限)\] | [ ] | 剩余期限（月）：[ ] |
| 全生命周期预期损失 | \[PD × LGD × EAD\] | [ ] | 阶段：□ Stage1 □ Stage2 □ Stage3 |

---

## 四、融资需求评估

| 项目 | 内容 | 备注 |
|------|------|------|
| 申请金额 | [ ] 万元 |  |
| 贷款用途 | □ 流动资金 □ 固定资产投资 □ 债务重组 □ 其他：[ ] | 多选/单选按授信政策 |
| 期限要求 | [ ] 年 | 是否含宽限期：[ ] 月 |
| 还款来源（第一） | [经营活动现金流 / 项目收入] | 核心测算依据：[ ] |
| 还款来源（第二） | [抵/质押物 / 保证人 / 其他] | 处置变现周期：[ ] 月 |
| 拟提供抵/质押物 | [ ] | 评估价值：[ ] 万元 |
| 抵/质押率 | [ ] % | 内部限额：[ ] % |

---

## 五、风险评级矩阵

| 风险类别 | 风险等级 (1-5分) | 关键风险点描述 | 缓释措施 | 责任人 | 跟踪频率 |
|----------|------------------|----------------|----------|--------|----------|
| 行业风险 | [ ] | [具体描述] | [应对措施] | [ ] | [ ] |
| 经营风险 | [ ] | [具体描述] | [应对措施] | [ ] | [ ] |
| 财务风险 | [ ] | [具体描述] | [应对措施] | [ ] | [ ] |
| 担保风险 | [ ] | [具体描述] | [应对措施] | [ ] | [ ] |
| 合规/法律风险 | [ ] | [具体描述] | [应对措施] | [ ] | [ ] |
| ESG/环保风险 | [ ] | [具体描述] | [应对措施] | [ ] | [ ] |

综合风险评级： [ ] （加权评分模型：权重设定说明：[ ]）  
最低缓释要求： [ ] （如需增信措施/降低授信敞口说明）

---

## 六、评估结论生成器

### （一）授信建议

建议授信额度： [ ] 万元 （不超过净资产的 [ ] %）  
建议利率： 年化 [ ] % （LPR [加/减] [ ] BP）  
建议担保方式： □ 抵押 □ 质押 □ 保证 □ 信用 □ 组合（说明：[ ]）  
拟抵/质押物概要： [ ]（覆盖率：[ ] %）  
建议还款方式： □ 等额本息 □ 等额本金 □ 分期付息到期还本 □ 其他：[ ]  
其他条件（先决条件 / 附加条款）：  
  1. [ ]  
  2. [ ]  

### （二）贷后管理要点

| 监控项目 | 指标定义 | 预警阈值 | 监测频率 | 处置预案 |
|----------|----------|----------|----------|----------|
| 重点监控指标1 | [ ] | [ ] | [月/季] | [ ] |
| 重点监控指标2 | [ ] | [ ] | [月/季] | [ ] |
| 现金流覆盖 | 经营现金流 / 当期还本付息额 | ≥[ ] | [月/季] | [措施] |
| 资产负债率 | 负债总额 / 资产总额 | ≤[ ] % | [季] | [措施] |
| 库存周转 | 销售成本 / 平均库存 | ≥[ ] 次/年 | [季] | [措施] |

风险预警阈值总览： [文字描述 / 附表]  
检查频率要求： [ ] （例：贷后首年季度检查，次年半年一次）  

---

## 七、附录（可选）

### 1. 抵质押物清单

| 序号 | 资产类型 | 权属证号 | 评估价值(万元) | 折扣率(%) | 折后价值(万元) | 备注 |
|------|----------|----------|----------------|-----------|----------------|------|
| 1 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| 2 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |

### 2. 保证人信息

| 保证人名称 | 类型(自然人/法人) | 关联关系 | 资信简述 | 提供材料 | 备注 |
|------------|------------------|----------|----------|----------|------|
| [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |

### 3. 关键假设与模型参数

| 模块 | 参数 | 数值 | 来源/口径 | 审核人 |
|------|------|------|----------|--------|
| 财务预测 | 销售增长率 | [ ] % | [ ] | [ ] |
| 财务预测 | 毛利率 | [ ] % | [ ] | [ ] |
| ECL | PD矩阵版本 | [ ] | 内部模型 | [ ] |
| ECL | LGD参数组 | [ ] | 抵押品回收历史 | [ ] |
"""


async def main() -> None:
    _install_stubs()

    # Ensure repository root is on sys.path for package import
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    # Import tools.py directly by path to avoid package __init__ side-effects
    tools_path = repo_root / "template_agent" / "src" / "tools.py"
    spec = importlib.util.spec_from_file_location("_temp_tools_module", tools_path)
    assert spec and spec.loader, f"Failed to load spec from {tools_path}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)  # type: ignore[arg-type]
    SplitMarkdownTreeTool = getattr(mod, "SplitMarkdownTreeTool")

    md = build_sample_markdown()
    tool = SplitMarkdownTreeTool()
    res = await tool.execute(markdown=md, include_content=False)

    if getattr(res, "error", None):
        print("Error:", res.error)
        return

    print("Outline:")
    print(res.output)

    try:
        data = json.loads(res.system or "{}")
    except Exception:
        data = {}

    print("\nSummary:")
    print("- doc_title:", data.get("doc_title"))
    print("- node_count:", data.get("node_count"))
    leaves = data.get("leaves") or []
    print("- leaves:")
    for leaf in leaves:
        path = leaf.get("path") or [leaf.get("title")]
        print("  -", " / ".join(str(x) for x in path))


if __name__ == "__main__":
    asyncio.run(main())
