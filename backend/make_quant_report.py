"""生成一篇「仿真·金融工程多因子选股研报」PDF，作为 report-reader 的中文测试样例。

说明：真实券商金工研报受版权/付费墙限制无法直接下载，本脚本用 PyMuPDF 现场合成一篇
结构完整、含带边框数据表与矢量图表(柱状/折线)的研报样式 PDF，供上传解析、表格抽取与
视觉识别调试使用。纯本地生成，不涉及任何外部数据。
"""
from __future__ import annotations

from pathlib import Path

import pymupdf as fitz

CJK = "china-s"
OUT = Path(__file__).resolve().parent.parent / "samples" / "cn_quant_金工多因子选股专题.pdf"
W, H = 595.3, 841.9  # A4 pt
INK = (0.12, 0.13, 0.16)
BLUE = (0.18, 0.34, 0.78)
RED = (0.78, 0.24, 0.26)
GREY = (0.5, 0.52, 0.55)


def para(page, rect, text, size=10.5, lead=1.5, color=INK):
    page.insert_textbox(rect, text, fontname=CJK, fontsize=size, lineheight=lead, color=color)


def title(page, text, y=72, size=19, color=INK):
    page.insert_text((56, y), text, fontname=CJK, fontsize=size, color=color)


def heading(page, text, y, size=13):
    page.insert_text((56, y), text, fontname=CJK, fontsize=size, color=BLUE)
    page.draw_line(fitz.Point(56, y + 5), fitz.Point(539, y + 5), color=(0.85, 0.87, 0.92), width=0.8)


def draw_table(page, x0, y0, headers, rows, col_w, row_h=22, font=9):
    total_w = sum(col_w)
    n = len(rows) + 1
    # 表头底纹
    page.draw_rect(fitz.Rect(x0, y0, x0 + total_w, y0 + row_h), color=None, fill=(0.93, 0.95, 0.99))
    # 网格
    for r in range(n + 1):
        page.draw_line(fitz.Point(x0, y0 + r * row_h), fitz.Point(x0 + total_w, y0 + r * row_h), color=(0.7, 0.72, 0.76), width=0.6)
    for c in range(len(headers) + 1):
        x = x0 + sum(col_w[:c])
        page.draw_line(fitz.Point(x, y0), fitz.Point(x, y0 + n * row_h), color=(0.7, 0.72, 0.76), width=0.6)
    # 文本
    for ci, hcell in enumerate(headers):
        page.insert_text((x0 + sum(col_w[:ci]) + 6, y0 + 15), hcell, fontname=CJK, fontsize=font, color=INK)
    for ri, row in enumerate(rows):
        for ci, cell in enumerate(row):
            page.insert_text((x0 + sum(col_w[:ci]) + 6, y0 + (ri + 1) * row_h + 15), cell, fontname=CJK, fontsize=font, color=INK)
    return y0 + n * row_h


def bar_chart(page, rect, labels, values, title_text, unit="%", vmax=None, color=BLUE):
    x0, y0, x1, y1 = rect
    page.insert_text((x0, y0 - 6), title_text, fontname=CJK, fontsize=10, color=INK)
    vmax = max(max(values), 0) if vmax is None else vmax
    vmin = min(min(values), 0)
    span = (vmax - vmin) or 1
    zero_y = y1 - (0 - vmin) / span * (y1 - y0)
    # 坐标轴
    page.draw_line(fitz.Point(x0, y0), fitz.Point(x0, y1), color=GREY, width=0.8)
    page.draw_line(fitz.Point(x0, zero_y), fitz.Point(x1, zero_y), color=GREY, width=0.8)
    n = len(values)
    slot = (x1 - x0) / n
    bw = slot * 0.6
    for i, v in enumerate(values):
        bx = x0 + i * slot + (slot - bw) / 2
        top = y1 - (max(v, 0) - vmin) / span * (y1 - y0)
        bot = y1 - (min(v, 0) - vmin) / span * (y1 - y0)
        page.draw_rect(fitz.Rect(bx, top, bx + bw, bot), color=None, fill=color)
        # 数值标注
        label = f"{v:g}{unit}"
        page.insert_text((bx + bw / 2 - len(label) * 2.2, (top if v >= 0 else bot) - 3), label, fontname=CJK, fontsize=7.5, color=INK)
        page.insert_text((bx + bw / 2 - len(labels[i]) * 3, y1 + 11), labels[i], fontname=CJK, fontsize=7.5, color=GREY)


def line_chart(page, rect, xs, ys, title_text, ylabels=None):
    x0, y0, x1, y1 = rect
    page.insert_text((x0, y0 - 6), title_text, fontname=CJK, fontsize=10, color=INK)
    vmax, vmin = max(ys), min(ys)
    span = (vmax - vmin) or 1
    # 网格与 y 轴刻度
    for k in range(5):
        gv = vmin + span * k / 4
        gy = y1 - (gv - vmin) / span * (y1 - y0)
        page.draw_line(fitz.Point(x0, gy), fitz.Point(x1, gy), color=(0.9, 0.91, 0.94), width=0.5)
        page.insert_text((x0 - 30, gy + 3), f"{gv:.2f}", fontname=CJK, fontsize=7, color=GREY)
    page.draw_line(fitz.Point(x0, y0), fitz.Point(x0, y1), color=GREY, width=0.8)
    n = len(ys)
    pts = []
    for i in range(n):
        px = x0 + (x1 - x0) * i / (n - 1)
        py = y1 - (ys[i] - vmin) / span * (y1 - y0)
        pts.append((px, py))
    for a, b in zip(pts, pts[1:]):
        page.draw_line(fitz.Point(*a), fitz.Point(*b), color=RED, width=1.4)
    for (px, py) in pts:
        page.draw_circle(fitz.Point(px, py), 1.8, color=RED, fill=RED)
    for i, lab in enumerate(xs):
        px = x0 + (x1 - x0) * i / (n - 1)
        page.insert_text((px - len(lab) * 2.6, y1 + 11), lab, fontname=CJK, fontsize=6.5, color=GREY)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()

    # ---- 第1页 封面 ----
    p = doc.new_page()
    p.draw_rect(fitz.Rect(0, 0, W, 4), color=None, fill=BLUE)
    title(p, "量化多因子选股框架专题", y=90, size=22)
    title(p, "——基于 Barra 风格因子的 Alpha 增强与分层验证", y=120, size=13, color=GREY)
    p.draw_line(fitz.Point(56, 140), fitz.Point(539, 140), color=(0.85, 0.87, 0.92), width=1)
    para(p, fitz.Rect(56, 156, 539, 200), "XX证券 · 金融工程研究组        发布日期：2026-09-15\n分析师：张 三  执业证书：S1450526000001   联系人：李 四", size=10, color=GREY)
    heading(p, "摘  要", 232)
    para(
        p, fitz.Rect(56, 250, 539, 470),
        "本文构建了一套以价值、成长、质量、动量、低波动与流动性六大类风格因子为核心的多因子选股框架。"
        "通过 Barra CNE6 风险模型对风格暴露与行业、市值进行中性化处理，采用半衰期加权 IC 与 ICIR 对因子进行有效性检验，"
        "并以十分组单调性与分层回测验证因子的区分能力。实证显示，20日反转与价值因子在 A 股中证全指范围内 ICIR 显著、"
        "多头组合相对基准具备稳定超额。等权合成的多因子组合在 2019-2025 年的样本外区间年化超额约 9.6%，"
        "最大回撤可控于 12% 以内，信息比率 1.35，具备较好的实盘可投资性。",
    )
    heading(p, "目  录", 495)
    para(p, fitz.Rect(56, 512, 539, 640), "一、因子体系与 IC 检验 ……… 2\n二、分层回测与超额表现 ……… 3\n三、组合构建与风险控制 ……… 4\n四、风险提示 ……… 4", size=10.5)

    # ---- 第2页 因子体系 + IC 表 ----
    p = doc.new_page()
    heading(p, "一、因子体系与 IC 检验", 72)
    para(
        p, fitz.Rect(56, 90, 539, 210),
        "我们从财务、量价与另类数据三个维度刻画个股Alpha。对每个候选因子，先做去极值(MAD)、"
        "标准化(Z-score)与市值行业中性化，再以未来 20 日收益为标签计算 Rank IC。"
        "下表给出六大类代表性因子在测试窗口内的统计表现，ICIR 大于 0.3 视为稳定可用。",
    )
    y = draw_table(
        p, 56, 236,
        ["因子", "IC均值", "ICIR", "多空年化", "单调性"],
        [
            ["价值 EP", "0.031", "0.42", "8.6%", "0.72"],
            ["成长 净利增速", "0.028", "0.35", "7.1%", "0.65"],
            ["质量 ROE", "0.025", "0.40", "6.8%", "0.68"],
            ["动量 20日反转", "0.035", "0.55", "11.2%", "0.78"],
            ["低波动", "0.019", "0.30", "4.5%", "0.55"],
            ["流动性", "0.022", "0.38", "5.9%", "0.60"],
        ],
        col_w=[150, 95, 85, 95, 85],
    )
    para(p, fitz.Rect(56, y + 18, 539, 620),
         "注：多空年化由因子十分组多头与空头组合年化收益之差衡量；单调性为分组收益与排序的 Spearman 相关。"
         "整体看，反转与价值在 A 股中短期具有最强的区分能力，质量因子胜在稳定，低波动在市场下行期具备防御属性。",
         size=9.5, color=GREY)

    # ---- 第3页 分层回测 图 ----
    p = doc.new_page()
    heading(p, "二、分层回测与超额表现", 72)
    para(p, fitz.Rect(56, 90, 539, 150),
         "以合成因子对股票池进行十分组排序，各组等权持有、按月调仓。下图左为各组年化收益，呈显著单调递减；"
         "下图右为多头组合相对中证全指的累计超额净值（起点 1.00）。", size=10.5)
    bar_chart(p, (70, 210, 300, 420),
              ["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10"],
              [25, 19, 15, 12, 9, 7, 5, 3, 1, -2],
              "图1  十分组年化收益率", unit="%")
    line_chart(p, (370, 210, 545, 420),
               ["19-01", "19-07", "20-01", "20-07", "21-01", "21-07", "22-01", "22-07", "23-01", "23-07", "24-01", "24-07"],
               [1.00, 1.09, 1.18, 1.27, 1.39, 1.48, 1.42, 1.53, 1.61, 1.70, 1.82, 1.96],
               "图2  累计超额净值")
    draw_table(
        p, 70, 470,
        ["分组", "年化收益", "年化波动", "夏普", "相对基准超额"],
        [["多头(D1)", "25.1%", "18.3%", "1.09", "9.6%"],
         ["空头(D10)", "-2.4%", "16.9%", "-0.30", "-17.9%"],
         ["多空(D1-D10)", "27.8%", "11.2%", "2.15", "12.4%"]],
        col_w=[120, 90, 90, 60, 110],
    )

    # ---- 第4页 组合构建 + 风险提示 ----
    p = doc.new_page()
    heading(p, "三、组合构建与风险控制", 72)
    para(p, fitz.Rect(56, 90, 539, 170),
         "组合采用优化器在中性化约束下最大化合成因子暴露，控制跟踪误差与个股集中度。主要风险约束如下表。", size=10.5)
    draw_table(
        p, 56, 196,
        ["约束项", "设定"],
        [["行业偏离", "相对基准 ±3%"],
         ["个股权重上限", "1.5%"],
         ["风格暴露", "|z| ≤ 0.3"],
         ["年化跟踪误差", "≤ 6%"],
         ["日均成交约束", "持仓需 2 日出清"]],
        col_w=[180, 320],
    )
    heading(p, "四、风险提示", 380)
    para(p, fitz.Rect(56, 398, 539, 520),
         "1）模型基于历史数据回测，因子有效性可能随市场风格切换而衰减；"
         "2）A 股交易成本、冲击成本与流动性约束可能在极端行情下放大回撤；"
         "3）量化策略在风格剧烈轮动或系统性风险事件中存在阶段性失效风险。本报告结论不构成投资建议。",
         size=10)

    doc.save(str(OUT))
    doc.close()
    print("生成:", OUT)


if __name__ == "__main__":
    main()
