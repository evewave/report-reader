---
name: 券商个股深度研报
category: 个股与公司
id: stock-deep
description: 针对上市公司个股深度研究报告，提炼投资评级、盈利预测、财务/估值数据与业务拆分，并把关键财务数据转成可交互图表。
version: 1.0.0
author: report-reader 内置
tags: 金融,研报,个股,买方视角
report_types: 券商研报,个股深度,首次覆盖
needs_vision: true
uses_text_model: true
---

聚焦个股投研要素：投资评级与目标价、核心投资逻辑、公司与行业地位、财务三表与盈利预测、估值方法（PE/PB/EV-EBITDA/DCF）、业务/收入拆分、催化剂与风险。

对图表的要求：优先还原「营业收入及增速」「归母净利润及增速」「毛利率/净利率走势」「分业务收入结构」「估值区间与可比公司对比」「盈利预测表」这类含明确数值序列的图，并给出可画图的 categories + series。目标价、评级、盈利预测等以 metrics / tables 承载。
