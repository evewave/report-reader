import React, { useEffect, useRef } from "react";
import * as echarts from "echarts";

const isDark = () => document.documentElement.getAttribute("data-theme") === "dark";

function themeVars() {
  const d = isDark();
  return {
    text: d ? "#c7cdda" : "#4a5568",
    strong: d ? "#e9ebf4" : "#1b2130",
    split: d ? "#2a3049" : "#eef0f6",
    axisLine: d ? "#3a4363" : "#d6dae8",
    ttBg: d ? "#1e2338" : "#ffffff",
    ttBorder: d ? "#384160" : "#e6e8f0",
    palette: d
      ? ["#8b98ff", "#ff9a5c", "#3ddc84", "#c79bff", "#ff7b80", "#3fd0e0", "#ffbf4d"]
      : ["#5b6cff", "#ff7a45", "#16a34a", "#a855f7", "#e5484d", "#0e97ad", "#d98600"],
  };
}

function buildOption(fig) {
  const T = themeVars();
  const cats = fig.categories || [];
  const series = fig.series || [];
  const type = fig.chart_type || "line";
  const base = {
    color: T.palette,
    textStyle: { color: T.text },
    tooltip: { trigger: "axis", confine: true, backgroundColor: T.ttBg, borderColor: T.ttBorder, textStyle: { color: T.strong } },
    legend: { type: "scroll", bottom: 0, textStyle: { color: T.text, fontSize: 11 } },
    grid: { left: 48, right: 48, top: 40, bottom: 56, containLabel: true },
    toolbox: { feature: { saveAsImage: { title: "保存图片" }, dataView: { title: "数据表" } }, right: 8, iconStyle: { borderColor: T.text } },
  };

  if (type === "pie") {
    const data = (series[0]?.data || []).map((v, i) => ({ name: cats[i] ?? `项${i + 1}`, value: v }));
    return {
      ...base,
      tooltip: { ...base.tooltip, trigger: "item" },
      series: [{ type: "pie", radius: ["40%", "66%"], center: ["50%", "45%"], data, label: { color: T.text, formatter: "{b}\n{d}%" } }],
    };
  }

  if (type === "radar") {
    const indicator = cats.map((c, i) => {
      let max = 0;
      series.forEach((s) => { const v = s.data?.[i]; if (typeof v === "number") max = Math.max(max, v); });
      return { name: c, max: max > 0 ? Math.ceil(max * 1.1) : 1 };
    });
    return {
      ...base,
      tooltip: { ...base.tooltip, trigger: "item" },
      radar: {
        indicator, radius: "62%", center: ["50%", "47%"],
        axisName: { color: T.text }, splitLine: { lineStyle: { color: T.split } },
        splitArea: { show: false }, axisLine: { lineStyle: { color: T.axisLine } },
      },
      series: [{ type: "radar", data: series.map((s) => ({ name: s.name, value: s.data || [] })) }],
    };
  }

  const twoAxis = series.some((s) => Number(s.yAxisIndex) === 1);
  const mkAxis = (name) => ({
    type: "value", name, nameTextStyle: { color: T.text },
    axisLabel: { fontSize: 11, color: T.text }, axisLine: { lineStyle: { color: T.axisLine } },
    splitLine: { lineStyle: { color: T.split } },
  });
  const yAxes = twoAxis ? [mkAxis(fig.unit || ""), { ...mkAxis(""), splitLine: { show: false } }] : [mkAxis(fig.unit || "")];

  return {
    ...base,
    xAxis: { type: "category", data: cats, axisLabel: { fontSize: 11, color: T.text, interval: "auto", rotate: cats.length > 7 ? 30 : 0 }, axisLine: { lineStyle: { color: T.axisLine } } },
    yAxis: yAxes,
    series: series.map((s) => {
      const t = s.type === "area" ? "line" : s.type || type;
      return {
        name: s.name, type: t, yAxisIndex: Number(s.yAxisIndex) || 0,
        smooth: t === "line", areaStyle: s.type === "area" ? { opacity: 0.18 } : undefined,
        symbol: t === "scatter" ? "circle" : undefined, barMaxWidth: 34, data: s.data || [],
      };
    }),
  };
}

export default function ChartCard({ figure, onJump }) {
  const elRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!elRef.current) return;
    const chart = echarts.init(elRef.current, null, { renderer: "canvas" });
    chartRef.current = chart;
    const render = () => {
      try { chart.setOption(buildOption(figure), true); }
      catch (e) { chart.setOption({ title: { text: "图表渲染失败：" + e.message, left: "center", top: "middle", textStyle: { fontSize: 12, color: "#999" } } }); }
    };
    render();
    const ro = new ResizeObserver(() => chart.resize());
    ro.observe(elRef.current);
    // 主题切换时重绘
    const mo = new MutationObserver(() => render());
    mo.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => { ro.disconnect(); mo.disconnect(); chart.dispose(); };
  }, [figure]);

  const hasData = (figure.series || []).some((s) => (s.data || []).length > 0);

  return (
    <div className="chart-card">
      <div className="ch">
        <span className="name">{figure.title}</span>
        {figure.estimated && <span className="badge est" title="数值为近似">≈ 近似</span>}
        {figure.source_page != null && (
          <button className="btn small jump" onClick={() => onJump && onJump(figure.source_page)}>定位第 {figure.source_page} 页</button>
        )}
      </div>
      {hasData ? <div className="el" ref={elRef} /> : <div className="hint" style={{ padding: 20, textAlign: "center" }}>未取到可绘图的数值</div>}
      {figure.insight && <div className="insight">💡 {figure.insight}</div>}
    </div>
  );
}
