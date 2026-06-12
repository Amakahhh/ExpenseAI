"use client";

import { useEffect, useRef } from "react";
import * as d3 from "d3";
import { MerchantStat } from "@/lib/api";

const CAT_COLOR: Record<string, string> = {
  food:"#F59E0B", transport:"#0EA5E9", entertainment:"#8B5CF6",
  bills:"#EF4444", health:"#EC4899", education:"#EAB308",
  shopping:"#F97316", other:"#6B7280",
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

    /* container */
    const g = svg.append("g");

    /* links — thin grey lines */
    const linkEls = g.append("g").selectAll("line").data(links).join("line")
      .attr("stroke", "#E0E0E0")
      .attr("stroke-width", (d) => 0.5 + d.strength);

    /* node groups */
    const dragBehavior = d3.drag<SVGGElement, GNode>()
      .on("start", (ev, d) => { if (!ev.active) sim.alphaTarget(0.25).restart(); d.fx = d.x; d.fy = d.y; })
      .on("drag",  (ev, d) => { d.fx = ev.x; d.fy = ev.y; })
      .on("end",   (ev, d) => { if (!ev.active) sim.alphaTarget(0); d.fx = null; d.fy = null; });

    const nodeG = g.append("g").selectAll("g").data(nodes).join("g")
      .attr("class", "cursor-grab active:cursor-grabbing")
      .call(dragBehavior as any);

    /* main circle — white fill, ink stroke */
    nodeG.append("circle")
      .attr("r", (d) => nodeR(d.total))
      .attr("fill", "#FFFFFF")
      .attr("stroke", "#111111")
      .attr("stroke-width", 1);

    /* label below node */
    nodeG.append("text")
      .attr("text-anchor", "middle")
      .attr("dy", (d) => nodeR(d.total) + 14)
      .attr("font-size", 10)
      .attr("font-family", "Inter, sans-serif")
      .attr("fill", "#AAAAAA")
      .attr("pointer-events", "none")
      .text((d) => d.id.split(" ").slice(0, 2).join(" ").slice(0, 14));

    /* hover */
    nodeG
      .on("mouseover", function (ev, d) {
        d3.select(this).select("circle")
          .transition().duration(120).attr("stroke", "#C07A10").attr("stroke-width", 2);
        if (!tipRef.current) return;
        const rect = el.getBoundingClientRect();
        tipRef.current.style.opacity = "1";
        tipRef.current.style.left   = `${ev.clientX - rect.left + 12}px`;
        tipRef.current.style.top    = `${ev.clientY - rect.top  - 12}px`;
        tipRef.current.innerHTML    = `
          <p style="font-size:13px;font-weight:600;color:#111111;margin-bottom:4px;font-family:Inter,sans-serif">${d.id}</p>
          <p style="font-size:12px;color:#777777;font-family:Inter,sans-serif">₦${d.total.toLocaleString("en-NG")}</p>
          <p style="font-size:11px;color:#AAAAAA;margin-top:2px;text-transform:capitalize;font-family:Inter,sans-serif">${d.category} · ${d.count} transactions</p>
        `;
      })
      .on("mouseout", function (_, d) {
        d3.select(this).select("circle")
          .transition().duration(120).attr("stroke", "#111111").attr("stroke-width", 1);
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
