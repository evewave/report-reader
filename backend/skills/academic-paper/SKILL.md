---
name: 学术论文精读
category: 学术与论文
id: academic-paper
description: 面向学术论文/预印本，提炼研究问题、方法、实验结果与结论，把消融/对比/收敛曲线等数据转成可交互图表，辅助快速精读。
version: 1.0.0
author: report-reader 内置
tags: 学术论文,paper,科研
report_types: 学术论文,预印本,论文精读
needs_vision: true
uses_text_model: true
---

聚焦科研要素：研究问题与动机、核心贡献、方法/模型架构、数据集与实验设置、主要结果与对比基线、消融实验、局限性与未来工作。

图表侧重：性能/精度对比（柱状）、指标随训练轮次/参数变化（折线）、消融实验差异、效率/复杂度对比、误差分布。把表格里可对比的数值整理成 categories + series。

阅读辅助：给出「一句话贡献」「关键公式含义的白话解释」「值得精读的章节与页码」。
