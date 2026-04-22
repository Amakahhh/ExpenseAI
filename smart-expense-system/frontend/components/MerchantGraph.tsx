"use client";

import { useEffect, useRef } from "react";
import * as d3 from "d3";
import { MerchantStat } from "@/lib/api";

const CAT_COLOR: Record<string, string> = {
  food:"#F59E0B", transport:"#00D4FF", entertainment:"#A855F7",
  bills:"#EF4444", health:"#EC4899", education:"#EAB308",
  shopping:"#F97316", other:"#6B6B8A",
};

interface GNode extends d3.SimulationNodeDatum {
  id: string; total: number; count: number; category: string;
}
interface GLink extends d3.SimulationLinkDatum<GNode> {
  strength: number;
}

export default function MerchantGraph({ merchants }: { merchants: MerchantStat[] }) {
  const svgRef     = useRef<SVGSVGElement>(null);
  const tipRef     = useRef<HTMLDivElement>(null);
  const simRef     = useRef<d3.Simulation<GNode, GLink> | null>(null);

  useEffect(() => {
    if (!svgRef.current || merchants.length === 0) return;

    const el     = svgRef.current;
    const W      = el.clientWidth  || 700;
    const H      = el.clientHeight || 420;
    const svg    = d3.select(el);
    svg.selectAll("*").remove();

    /* nodes */
    const nodes: GNode[] = merchants.map((m) => ({
      id: m.merchant, total: m.total, count: m.count,
      category: (m as any).category || "other",
    }));

    /* edges: connect nodes that share a category */
    const links: GLink[] = [];
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        if (nodes[i].category === nodes[j].category) {
          const ratio = Math.min(nodes[i].total, nodes[j].total) /
            (Math.max(nodes[i].total, nodes[j].total) || 1);
          links.push({ source: nodes[i].id, target: nodes[j].id, strength: ratio });
        }
      }
    }

    const maxTotal  = Math.max(...nodes.map((n) => n.total), 1);
    const nodeR     = (t: number) => 9 + (t / maxTotal) * 22;

    /* defs */
    const defs = svg.append("defs");
    const glow = defs.append("filter").attr("id", "glow-filter");
    glow.append("feGaussianBlur").attr("stdDeviation", "3").attr("result", "blur");
    const merge = glow.append("feMerge");
    merge.append("feMergeNode").attr("in", "blur");
    merge.append("feMergeNode").attr("in", "SourceGraphic");

    /* container */
    const g = svg.append("g");

    /* links */
    const linkEls = g.append("g").selectAll("line").data(links).join("line")
      .attr("stroke", "rgba(108,99,255,0.18)")
      .attr("stroke-width", (d) => 0.5 + d.strength * 1.5)
      .attr("stroke-dasharray", "800")
      .attr("stroke-dashoffset", "800")
      .style("animation", (_, i) => `drawEdge 1.4s ease ${i * 0.08}s forwards`);

    /* node groups */
    const dragBehavior = d3.drag<SVGGElement, GNode>()
      .on("start", (ev, d) => { if (!ev.active) sim.alphaTarget(0.25).restart(); d.fx = d.x; d.fy = d.y; })
      .on("drag",  (ev, d) => { d.fx = ev.x; d.fy = ev.y; })
      .on("end",   (ev, d) => { if (!ev.active) sim.alphaTarget(0); d.fx = null; d.fy = null; });

    const nodeG = g.append("g").selectAll("g").data(nodes).join("g")
      .attr("class", "cursor-grab active:cursor-grabbing")
      .call(dragBehavior as any);

    /* outer glow ring */
    nodeG.append("circle")
      .attr("r", (d) => nodeR(d.total) + 8)
      .attr("fill", (d) => CAT_COLOR[d.category] || "#6B6B8A")
      .attr("opacity", 0.08);

    /* main circle */
    nodeG.append("circle")
      .attr("r", (d) => nodeR(d.total))
      .attr("fill", (d) => `${CAT_COLOR[d.category] || "#6B6B8A"}CC`)
      .attr("stroke", (d) => CAT_COLOR[d.category] || "#6B6B8A")
      .attr("stroke-width", 1.2)
      .attr("filter", "url(#glow-filter)");

    /* label */
    nodeG.append("text")
      .attr("text-anchor", "middle").attr("dy", "0.35em")
      .attr("font-size", 8).attr("font-family", "var(--font-mono)")
      .attr("fill", "#F0F0FF").attr("pointer-events", "none")
      .text((d) => d.id.split(" ").slice(0, 2).join(" ").slice(0, 10));

    /* hover */
    nodeG
      .on("mouseover", function (ev, d) {
        d3.select(this).select("circle:nth-child(2)")
          .transition().duration(180).attr("r", nodeR(d.total) * 1.28);
        if (!tipRef.current) return;
        const rect = el.getBoundingClientRect();
        tipRef.current.style.opacity = "1";
        tipRef.current.style.left   = `${ev.clientX - rect.left + 12}px`;
        tipRef.current.style.top    = `${ev.clientY - rect.top  - 12}px`;
        tipRef.current.innerHTML    = `
          <p style="font-family:var(--font-display);font-size:13px;font-weight:600;color:#F0F0FF;margin-bottom:4px">${d.id}</p>
          <p style="font-family:var(--font-mono);font-size:11px;color:#00D4FF">₦${d.total.toLocaleString("en-NG")}</p>
          <p style="font-family:var(--font-mono);font-size:10px;color:#6B6B8A;margin-top:2px;text-transform:capitalize">${d.category} · ${d.count}×</p>
        `;
      })
      .on("mouseout", function (_, d) {
        d3.select(this).select("circle:nth-child(2)")
          .transition().duration(180).attr("r", nodeR(d.total));
        if (tipRef.current) tipRef.current.style.opacity = "0";
      });

    /* simulation */
    const sim = d3.forceSimulation(nodes)
      .force("link",      d3.forceLink<GNode, GLink>(links).id((d) => d.id).distance(90).strength(0.25))
      .force("charge",    d3.forceManyBody().strength(-180))
      .force("center",    d3.forceCenter(W / 2, H / 2))
      .force("collision", d3.forceCollide<GNode>().radius((d) => nodeR(d.total) + 12));

    sim.on("tick", () => {
      linkEls
        .attr("x1", (d: any) => d.source.x).attr("y1", (d: any) => d.source.y)
        .attr("x2", (d: any) => d.target.x).attr("y2", (d: any) => d.target.y);
      nodeG.attr("transform", (d: any) => `translate(${d.x},${d.y})`);
    });

    simRef.current = sim as any;
    return () => { sim.stop(); };
  }, [merchants]);

  return (
    <div className="relative w-full h-full">
      <svg ref={svgRef} width="100%" height="100%" style={{ overflow: "visible" }} />
      <div ref={tipRef} className="graph-tooltip" />
    </div>
  );
}
