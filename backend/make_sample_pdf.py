"""生成一个带边框表格与多年数值序列的样例研报 PDF，用于端到端测试。"""
import pymupdf as fitz
from pathlib import Path

out = Path("data/_tmp")
out.mkdir(parents=True, exist_ok=True)
doc = fitz.open()

# ---- 第 1 页：标题 + 概述 ----
p = doc.new_page()
p.insert_text((56, 70), "XX科技（600001.SH）深度研究报告", fontsize=18)
p.insert_text((56, 100), "投资评级：买入    目标价：45.0 元    现价：32.6 元", fontsize=12)
body = [
    "公司概况：XX科技是国内领先的智能装备制造商，主营工业自动化与新能源装备两大业务。",
    "核心逻辑：受益于下游资本开支上行与国产替代，公司订单持续高增，盈利能力稳步提升。",
    "财务概览：2021-2023 年营业收入从 100 亿元增长至 165 亿元，归母净利润由 8 亿元增至 18 亿元。",
    "毛利率同期由 25% 提升至 32%，主要源于高毛利的新能源装备占比提升。",
    "风险提示：下游需求不及预期、原材料价格波动、行业竞争加剧。",
]
y = 140
for line in body:
    p.insert_text((56, y), line, fontsize=11)
    y += 22

# ---- 第 2 页：盈利预测表格（带边框，可被 find_tables 识别）----
p2 = doc.new_page()
p2.insert_text((56, 60), "表 1：公司财务预测摘要（单位：亿元）", fontsize=12)
headers = ["指标", "2021", "2022", "2023", "2024E", "2025E"]
rows = [
    ["营业收入", "100", "130", "165", "205", "250"],
    ["归母净利润", "8", "12", "18", "24", "31"],
    ["毛利率(%)", "25", "28", "32", "33", "34"],
    ["净利率(%)", "8", "9.2", "10.9", "11.7", "12.4"],
    ["EPS(元)", "0.8", "1.2", "1.8", "2.4", "3.1"],
]
x0, y0 = 56, 90
col_w = [90] + [62] * 5
row_h = 26
# 画网格
for r in range(len(rows) + 1):
    p2.draw_line(fitz.Point(x0, y0 + r * row_h), fitz.Point(x0 + sum(col_w), y0 + r * row_h), width=0.6)
for c in range(len(headers) + 1):
    x = x0 + sum(col_w[:c])
    p2.draw_line(fitz.Point(x, y0), fitz.Point(x, y0 + (len(rows) + 1) * row_h), width=0.6)
# 填文字
all_rows = [headers] + rows
for ri, row in enumerate(all_rows):
    for ci, cell in enumerate(row):
        p2.insert_text((x0 + sum(col_w[:ci]) + 6, y0 + ri * row_h + 17), cell, fontsize=10)

# ---- 第 3 页：分业务收入 ----
p3 = doc.new_page()
p3.insert_text((56, 60), "表 2：2023 年分业务收入结构（单位：亿元）", fontsize=12)
headers2 = ["业务", "收入", "占比(%)", "同比(%)"]
rows2 = [
    ["工业自动化", "95", "57.6", "22"],
    ["新能源装备", "60", "36.4", "55"],
    ["其他", "10", "6.0", "-5"],
]
x0, y0 = 56, 90
col_w2 = [120, 80, 80, 80]
for r in range(len(rows2) + 1):
    p3.draw_line(fitz.Point(x0, y0 + r * row_h), fitz.Point(x0 + sum(col_w2), y0 + r * row_h), width=0.6)
for c in range(len(headers2) + 1):
    x = x0 + sum(col_w2[:c])
    p3.draw_line(fitz.Point(x, y0), fitz.Point(x, y0 + (len(rows2) + 1) * row_h), width=0.6)
for ri, row in enumerate([headers2] + rows2):
    for ci, cell in enumerate(row):
        p3.insert_text((x0 + sum(col_w2[:ci]) + 6, y0 + ri * row_h + 17), cell, fontsize=10)

doc.save(str(out / "sample.pdf"))
doc.close()
print("saved data/_tmp/sample.pdf")
