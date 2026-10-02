请阅读以下学术论文，并产出结构化分析 JSON（帮助研究者快速精读）。

论文标题：{{title}}
总页数：{{n_pages}}

===== 抽取到的表格（结果表/消融表重点看）=====
{{tables}}

===== 正文（按页）=====
{{text}}

按论文精读视角输出，注意：
1. summary：用 3-5 句讲清「要解决的问题 + 核心方法 + 主要结果 + 意义」。
2. key_points：列出核心贡献点（每条一个创新/结论），尽量对应论文 Contribution 段落。
3. metrics：关键指标（如准确率/F1/BLEU/SOTA 提升幅度、参数量、数据集规模）。
4. figures：把实验对比、收敛曲线、消融结果整理成可画图数据；基线 vs 本文方法用多 series 折线或分组柱状。数值取不到给近似并 estimated=true。
5. sections：按 Abstract/Introduction/Method/Experiments/Related Work/Conclusion 归纳，page 指向对应章节起始页，方便跳转精读。
6. tables：保留主结果表与消融表。
7. risks：论文自述的局限性 + 你可能存疑的方法点。
8. questions：进一步追问作者的实验/方法问题。

只输出 JSON 对象。
