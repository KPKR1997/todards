"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { getDashboard } from "./api";
import type { DashboardData, NullableNumber, Run, TrendPoint } from "../types/observatory";

const STAGE_COLOURS: Record<string, string> = {
  scrape: "#bd6048",
  guardrails: "#b98735",
  deduplication: "#8a9b77",
  category_validation: "#577b8d",
  ranking: "#756592",
  processing: "#183c3a",
  assembly: "#bcb4a7",
};

const CATEGORY_COLOURS = ["#183c3a", "#bd6048", "#b98735", "#667c72", "#7d7089", "#8195a4"];

function number(value: NullableNumber, digits = 0): string {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: digits, minimumFractionDigits: digits }).format(value);
}

function compact(value: NullableNumber): string {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

function duration(seconds: NullableNumber): string {
  if (seconds === null || seconds === undefined) return "—";
  if (seconds < 60) return `${number(seconds, 0)}s`;
  if (seconds < 3600) return `${number(seconds / 60, 1)}m`;
  return `${number(seconds / 3600, 1)}h`;
}

function dateTime(value: string | null): string {
  if (!value) return "Unavailable";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString("en-GB", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

function shortTime(value: string | number | null | undefined): string {
  if (typeof value !== "string") return "";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <section className={`rounded-[22px] border border-line/90 bg-white/80 shadow-panel ${className}`}>{children}</section>;
}

function Kpi({ label, value, detail, accent = "pine" }: { label: string; value: string; detail: string; accent?: "pine" | "terracotta" | "gold" | "slate" }) {
  const colour = { pine: "bg-pine", terracotta: "bg-terracotta", gold: "bg-gold", slate: "bg-[#6f8290]" }[accent];
  return (
    <Card className="relative overflow-hidden px-5 pb-5 pt-4">
      <span className={`absolute left-0 top-0 h-1 w-full ${colour}`} />
      <p className="text-[11px] font-bold uppercase tracking-[0.17em] text-stone-500">{label}</p>
      <p className="mt-3 font-serif text-[31px] font-semibold tracking-[-0.04em] text-ink">{value}</p>
      <p className="mt-1 min-h-5 text-xs leading-5 text-stone-500">{detail}</p>
    </Card>
  );
}

function PanelTitle({ eyebrow, title, trailing }: { eyebrow: string; title: string; trailing?: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-3 px-5 pt-5 sm:px-6 sm:pt-6">
      <div>
        <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-terracotta">{eyebrow}</p>
        <h2 className="mt-1 font-serif text-[22px] font-semibold tracking-[-0.025em] text-ink">{title}</h2>
      </div>
      {trailing}
    </div>
  );
}

function ChartTooltip({ active, payload, label, formatter }: { active?: boolean; payload?: { name?: string; value?: number; color?: string }[]; label?: string; formatter?: (value: number, name?: string) => string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl border border-line bg-[#fffdfa] px-3 py-2 shadow-lg">
      <p className="mb-1 text-[11px] font-semibold text-stone-600">{shortTime(label)}</p>
      {payload.map((entry, index) => (
        <p className="text-xs text-ink" key={`${entry.name}-${index}`}>
          <span className="mr-1 inline-block h-2 w-2 rounded-full" style={{ backgroundColor: entry.color }} />
          {entry.name}: <strong>{formatter ? formatter(entry.value ?? 0, entry.name) : number(entry.value ?? null)}</strong>
        </p>
      ))}
    </div>
  );
}

function DurationTrend({ trend, p50 }: { trend: TrendPoint[]; p50: NullableNumber }) {
  return (
    <Card className="min-h-[356px]">
      <PanelTitle eyebrow="Pipeline pace" title="Run duration over time" trailing={<span className="rounded-full bg-[#e8f0ec] px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-pine">Individual runs</span>} />
      <div className="h-[246px] px-2 pb-3 pt-4 sm:px-4">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={trend} margin={{ top: 6, right: 10, left: -16, bottom: 2 }}>
            <defs>
              <linearGradient id="durationWash" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor="#bd6048" stopOpacity={0.28} />
                <stop offset="100%" stopColor="#bd6048" stopOpacity={0.01} />
              </linearGradient>
            </defs>
            <CartesianGrid vertical={false} stroke="#e8e2d9" strokeDasharray="3 4" />
            <XAxis dataKey="timestamp" tickFormatter={shortTime} tick={{ fontSize: 10, fill: "#756e66" }} axisLine={false} tickLine={false} minTickGap={26} />
            <YAxis tickFormatter={(value: number) => duration(value)} tick={{ fontSize: 10, fill: "#756e66" }} axisLine={false} tickLine={false} width={43} />
            <Tooltip content={<ChartTooltip formatter={(value) => duration(value)} />} />
            <Area type="monotone" dataKey="duration_seconds" name="Duration" stroke="#bd6048" strokeWidth={2.5} fill="url(#durationWash)" connectNulls />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <p className="border-t border-line/75 px-5 py-3 text-xs leading-5 text-stone-500 sm:px-6">P50 {duration(p50)} · chart uses raw, complete run durations only.</p>
    </Card>
  );
}

function StageAverage({ data }: { data: DashboardData }) {
  return (
    <Card className="min-h-[356px]">
      <PanelTitle eyebrow="Where time goes" title="Average stage duration" trailing={<span className="text-xs text-stone-500">seconds / run</span>} />
      <div className="h-[246px] px-2 pb-2 pt-4 sm:px-4">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={[...data.stages.summary].reverse()} layout="vertical" margin={{ top: 3, right: 24, left: 20, bottom: 2 }}>
            <CartesianGrid horizontal={false} stroke="#ece7df" />
            <XAxis type="number" tickFormatter={(value: number) => duration(value)} tick={{ fontSize: 10, fill: "#756e66" }} axisLine={false} tickLine={false} />
            <YAxis type="category" dataKey="label" width={106} tick={{ fontSize: 10, fill: "#4f4b46" }} axisLine={false} tickLine={false} />
            <Tooltip content={<ChartTooltip formatter={(value) => duration(value)} />} cursor={{ fill: "#f5f0e9" }} />
            <Bar dataKey="average" name="Average" radius={[0, 7, 7, 0]} barSize={14}>
              {data.stages.summary.slice().reverse().map((stage) => <Cell key={stage.id} fill={STAGE_COLOURS[stage.id]} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="border-t border-line/75 px-5 py-3 text-xs leading-5 text-stone-500 sm:px-6">{data.overview.slowest_stage ? `${data.overview.slowest_stage.label} is the slowest measured stage on average.` : "No measured stages in this period."}</p>
    </Card>
  );
}

function ProcessFunnel({ data }: { data: DashboardData }) {
  const largest = Math.max(1, ...data.content.funnel.map((item) => item.value ?? 0));
  return (
    <Card className="min-h-[405px]">
      <PanelTitle eyebrow="Content movement" title="Observed processing counts" trailing={<span className="rounded-full bg-[#f5eee7] px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-terracotta">Diagnostic</span>} />
      <div className="space-y-3 px-5 py-5 sm:px-6">
        {data.content.funnel.map((item, index) => {
          const value = item.value ?? 0;
          const width = Math.max(12, value / largest * 100);
          return (
            <div key={item.id} className="grid grid-cols-[115px_1fr_46px] items-center gap-2 sm:grid-cols-[137px_1fr_54px]">
              <p className="text-xs font-medium text-stone-700">{item.label}</p>
              <div className="h-7 overflow-hidden rounded-md bg-[#efe9e1]">
                <div className="h-full rounded-md transition-all" style={{ width: `${width}%`, backgroundColor: ["#183c3a", "#56766e", "#b98735", "#bd6048", "#7d7089", "#243339"][index] }} />
              </div>
              <p className="text-right font-serif text-base font-semibold text-ink">{number(item.value)}</p>
            </div>
          );
        })}
      </div>
      <p className="border-t border-line/75 px-5 py-3 text-xs leading-5 text-stone-500 sm:px-6">Counts can overlap or describe different stages; this is not a strict conversion funnel.</p>
    </Card>
  );
}

function CategoryMix({ data }: { data: DashboardData }) {
  return (
    <Card className="min-h-[405px]">
      <PanelTitle eyebrow="Source intake" title="Scraped articles by category" trailing={<span className="text-xs text-stone-500">selected period</span>} />
      <div className="h-[240px] px-2 pb-2 pt-4 sm:px-4">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data.content.category_totals} margin={{ top: 2, right: 8, left: -18, bottom: 7 }}>
            <CartesianGrid vertical={false} stroke="#e8e2d9" strokeDasharray="3 4" />
            <XAxis dataKey="category" interval={0} angle={-22} textAnchor="end" height={60} tick={{ fontSize: 9, fill: "#756e66" }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 10, fill: "#756e66" }} axisLine={false} tickLine={false} width={28} />
            <Tooltip content={<ChartTooltip formatter={(value) => `${number(value)} articles`} />} />
            <Bar dataKey="articles" name="Articles" radius={[6, 6, 0, 0]} maxBarSize={38}>
              {data.content.category_totals.map((category, index) => <Cell key={category.category} fill={CATEGORY_COLOURS[index % CATEGORY_COLOURS.length]} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="border-t border-line/75 px-5 py-3 text-xs leading-5 text-stone-500 sm:px-6">Blank category cells are unavailable, not silently converted to zero.</p>
    </Card>
  );
}

function LlmPanel({ data }: { data: DashboardData }) {
  return (
    <Card>
      <PanelTitle eyebrow="Model telemetry" title="LLM time decomposition" trailing={<span className="text-xs text-stone-500">seconds / run</span>} />
      <div className="h-[236px] px-2 pb-2 pt-4 sm:px-4">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data.llm.trend} margin={{ top: 6, right: 10, left: -15, bottom: 2 }}>
            <CartesianGrid vertical={false} stroke="#e8e2d9" strokeDasharray="3 4" />
            <XAxis dataKey="timestamp" tickFormatter={shortTime} tick={{ fontSize: 10, fill: "#756e66" }} axisLine={false} tickLine={false} minTickGap={26} />
            <YAxis tickFormatter={(value: number) => duration(value)} tick={{ fontSize: 10, fill: "#756e66" }} axisLine={false} tickLine={false} width={40} />
            <Tooltip content={<ChartTooltip formatter={(value) => duration(value)} />} />
            <Legend wrapperStyle={{ fontSize: 10, paddingTop: 8 }} iconType="circle" />
            <Line type="monotone" dataKey="prompt_eval_seconds" name="Prompt eval" stroke="#b98735" strokeWidth={2} dot={false} connectNulls />
            <Line type="monotone" dataKey="generation_seconds" name="Generation" stroke="#bd6048" strokeWidth={2} dot={false} connectNulls />
            <Line type="monotone" dataKey="load_seconds" name="Model load" stroke="#577b8d" strokeWidth={2} dot={false} connectNulls />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="grid grid-cols-2 border-t border-line/75 sm:grid-cols-4">
        <Stat label="Calls" value={number(data.llm.total_calls)} />
        <Stat label="Failures" value={number(data.llm.total_failures)} />
        <Stat label="Failure rate" value={data.llm.failure_rate_percent === null ? "—" : `${number(data.llm.failure_rate_percent, 1)}%`} />
        <Stat label="Avg response" value={duration(data.llm.weighted_average_response_time_seconds)} />
      </div>
    </Card>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return <div className="border-b border-r border-line/75 px-4 py-3 last:border-r-0 sm:border-b-0"><p className="text-[10px] font-bold uppercase tracking-[.15em] text-stone-500">{label}</p><p className="mt-1 font-serif text-lg font-semibold text-ink">{value}</p></div>;
}

function RunBreakdown({ run, stageLabels }: { run: Run | null; stageLabels: Record<string, string> }) {
  const rows = run ? Object.entries(run.stages).map(([id, value]) => ({ id, label: stageLabels[id] ?? id, seconds: value })) : [];
  return (
    <Card>
      <PanelTitle eyebrow="Single-run lens" title="Selected run breakdown" trailing={run ? <span className="text-xs text-stone-500">{dateTime(run.timestamp)}</span> : undefined} />
      {run ? (
        <>
          <div className="h-[230px] px-2 pb-2 pt-4 sm:px-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={rows.reverse()} layout="vertical" margin={{ top: 2, right: 24, left: 18, bottom: 2 }}>
                <XAxis type="number" tickFormatter={(value: number) => duration(value)} tick={{ fontSize: 10, fill: "#756e66" }} axisLine={false} tickLine={false} />
                <YAxis type="category" dataKey="label" width={104} tick={{ fontSize: 10, fill: "#4f4b46" }} axisLine={false} tickLine={false} />
                <Tooltip content={<ChartTooltip formatter={(value) => duration(value)} />} />
                <Bar dataKey="seconds" name="Duration" radius={[0, 6, 6, 0]} barSize={14} fill="#183c3a" />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="grid grid-cols-3 border-t border-line/75">
            <Stat label="Overall" value={duration(run.duration_seconds)} />
            <Stat label="Scraped" value={number(run.scraped)} />
            <Stat label="Published" value={number(run.final_articles)} />
          </div>
        </>
      ) : <p className="px-5 py-12 text-sm text-stone-500">No run in the selected period.</p>}
    </Card>
  );
}

function QualityPanel({ data }: { data: DashboardData }) {
  const safety = data.safety.values;
  const latest = data.overview.latest_run;
  return (
    <Card className="overflow-hidden">
      <PanelTitle eyebrow="Instrumentation quality" title="What the telemetry can support" />
      <div className="grid divide-y divide-line/75 sm:grid-cols-2 sm:divide-x sm:divide-y-0">
        <div className="p-5 sm:p-6">
          <p className="text-[11px] font-bold uppercase tracking-[.15em] text-stone-500">Coverage</p>
          <div className="mt-4 space-y-4">
            <Coverage label="Run duration" value={data.meta.source.field_coverage_percent.duration_seconds ?? 0} />
            <Coverage label="LLM token usage" value={data.meta.source.field_coverage_percent.llm_performance_total_tokens ?? 0} />
            <Coverage label="Article safety" value={data.safety.coverage_percent} />
          </div>
        </div>
        <div className="p-5 sm:p-6">
          <p className="text-[11px] font-bold uppercase tracking-[.15em] text-stone-500">Safety diagnostics</p>
          <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
            <MiniMetric label="Articles seen" value={number(safety.articles_seen)} />
            <MiniMetric label="Classified unsafe" value={number(safety.classified_unsafe)} />
            <MiniMetric label="Model errors" value={number(safety.model_errors)} />
            <MiniMetric label="Dry-run rows" value={number(data.safety.dry_run_rows)} />
          </div>
          <p className="mt-4 text-xs leading-5 text-stone-500">Latest validation: {latest?.category_validation_status ?? "unavailable"}. Whole-pipeline success is intentionally not inferred from this stage.</p>
        </div>
      </div>
    </Card>
  );
}

function Coverage({ label, value }: { label: string; value: number }) {
  return <div><div className="mb-1.5 flex justify-between text-xs"><span className="text-stone-600">{label}</span><span className="font-semibold text-ink">{number(value, 1)}%</span></div><div className="h-1.5 overflow-hidden rounded-full bg-[#ebe5dc]"><div className="h-full rounded-full bg-pine" style={{ width: `${Math.min(100, value)}%` }} /></div></div>;
}

function MiniMetric({ label, value }: { label: string; value: string }) {
  return <div><p className="font-serif text-xl font-semibold text-ink">{value}</p><p className="text-[11px] leading-4 text-stone-500">{label}</p></div>;
}

function RunLedger({ data, selectedRunId, onSelect }: { data: DashboardData; selectedRunId: string | null; onSelect: (runId: string) => void }) {
  return (
    <Card className="overflow-hidden">
      <PanelTitle eyebrow="Traceability" title="Run ledger" trailing={<span className="text-xs text-stone-500">{data.runs.length} visible</span>} />
      <div className="overflow-x-auto px-2 pb-2 pt-4 sm:px-4">
        <table className="min-w-[690px] w-full border-separate border-spacing-0 text-left">
          <thead><tr className="text-[10px] font-bold uppercase tracking-[.14em] text-stone-500"><th className="px-3 py-2">Timestamp</th><th className="px-3 py-2">Duration</th><th className="px-3 py-2">Scraped</th><th className="px-3 py-2">Final</th><th className="px-3 py-2">LLM calls</th><th className="px-3 py-2">Tokens</th><th className="px-3 py-2">Stage status</th></tr></thead>
          <tbody>
            {data.runs.slice(0, 12).map((run) => <tr key={run.run_id} onClick={() => onSelect(run.run_id)} className={`cursor-pointer transition-colors hover:bg-[#f6f1ea] ${selectedRunId === run.run_id ? "bg-[#eef3ef]" : ""}`}>
              <td className="border-t border-line/70 px-3 py-3 text-xs font-medium text-ink">{dateTime(run.timestamp)}</td>
              <td className="border-t border-line/70 px-3 py-3 text-xs text-stone-600">{duration(run.duration_seconds)}</td>
              <td className="border-t border-line/70 px-3 py-3 text-xs text-stone-600">{number(run.scraped)}</td>
              <td className="border-t border-line/70 px-3 py-3 text-xs text-stone-600">{number(run.final_articles)}</td>
              <td className="border-t border-line/70 px-3 py-3 text-xs text-stone-600">{number(run.llm_calls)}</td>
              <td className="border-t border-line/70 px-3 py-3 text-xs text-stone-600">{compact(run.total_tokens)}</td>
              <td className="border-t border-line/70 px-3 py-3"><span className={`rounded-full px-2 py-1 text-[10px] font-bold uppercase tracking-wider ${run.category_validation_status === "completed" ? "bg-[#e8f0ec] text-pine" : "bg-[#f4e7df] text-terracotta"}`}>{run.category_validation_status ?? "unavailable"}</span></td>
            </tr>)}
          </tbody>
        </table>
      </div>
      <p className="border-t border-line/75 px-5 py-3 text-xs text-stone-500">Select a run to inspect its recorded stage profile. Showing the 12 most recent runs.</p>
    </Card>
  );
}

function EmptyState({ error, retry }: { error: string; retry: () => void }) {
  return <main className="flex min-h-screen items-center justify-center bg-paper px-5"><Card className="max-w-xl p-8"><p className="text-[10px] font-bold uppercase tracking-[.2em] text-terracotta">Todards Observatory</p><h1 className="mt-2 font-serif text-3xl font-semibold">Telemetry is not available</h1><p className="mt-3 text-sm leading-6 text-stone-600">{error}</p><p className="mt-3 text-sm leading-6 text-stone-600">Start the read-only FastAPI service and confirm that <code className="rounded bg-[#eee8df] px-1.5 py-0.5">reports/performance_history.csv</code> is reachable. No sample data is substituted.</p><button onClick={retry} className="mt-6 rounded-full bg-pine px-4 py-2 text-sm font-semibold text-white transition hover:bg-[#0e2928]">Try again</button></Card></main>;
}

export function ObservatoryDashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const received = await getDashboard(dateFrom || undefined, dateTo || undefined);
      setData(received);
      setSelectedRunId((current) => current && received.runs.some((run) => run.run_id === current) ? current : received.runs[0]?.run_id ?? null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not load telemetry.");
    } finally {
      setLoading(false);
    }
  };

  const clearFilters = async () => {
    setDateFrom("");
    setDateTo("");
    setLoading(true);
    setError(null);
    try {
      const received = await getDashboard();
      setData(received);
      setSelectedRunId(received.runs[0]?.run_id ?? null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not load telemetry.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []); // Initial load intentionally has no filters.

  const selectedRun = useMemo(() => data?.runs.find((run) => run.run_id === selectedRunId) ?? null, [data, selectedRunId]);
  const stageLabels = useMemo(() => Object.fromEntries((data?.stages.summary ?? []).map((stage) => [stage.id, stage.label])), [data]);

  if (loading && !data) return <main className="grid min-h-screen place-items-center bg-paper"><div className="text-center"><p className="font-serif text-3xl font-semibold text-ink">Todards.</p><p className="mt-2 text-sm text-stone-500">Reading pipeline telemetry…</p></div></main>;
  if (error && !data) return <EmptyState error={error} retry={() => void load()} />;
  if (!data) return null;

  const latest = data.overview.latest_run;
  return (
    <main className="min-h-screen bg-paper text-ink">
      <header className="border-b border-line/90 bg-[#faf8f4]/90">
        <div className="mx-auto flex max-w-[1440px] flex-wrap items-center justify-between gap-4 px-5 py-5 sm:px-8 lg:px-12">
          <a className="font-serif text-[34px] font-bold tracking-[-0.065em] text-ink" href="#top">Todards.</a>
          <p className="hidden max-w-[590px] text-center font-['cursive'] text-[17px] leading-6 text-stone-600 md:block">Quietly watching the machinery behind the stories that matter.</p>
          <span className="rounded-full border border-line bg-white px-3.5 py-2 text-xs font-semibold text-ink">Read-only telemetry</span>
        </div>
      </header>
      <div className="border-b border-line/70 bg-[#f2eee7]/70">
        <div className="mx-auto flex max-w-[1440px] items-center justify-between gap-4 overflow-x-auto px-5 py-3 text-[11px] font-bold uppercase tracking-[.16em] sm:px-8 lg:px-12">
          <div className="flex min-w-max gap-6 text-stone-500"><span className="text-pine">Observatory</span><span>Pipeline</span><span>Content quality</span><span>Model telemetry</span></div>
          <span className="min-w-max text-stone-500">{data.meta.selected_row_count} runs in view</span>
        </div>
      </div>

      <div id="top" className="mx-auto max-w-[1440px] px-5 pb-12 pt-8 sm:px-8 lg:px-12 lg:pt-10">
        <div className="flex flex-col justify-between gap-6 xl:flex-row xl:items-end">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[.2em] text-terracotta">Model & pipeline observatory</p>
            <h1 className="mt-2 max-w-3xl font-serif text-[38px] font-semibold leading-[1.04] tracking-[-0.045em] text-ink sm:text-[50px]">A clear view of each Todards run.</h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-stone-600">Execution pace, content movement, safety signals and LLM workload—calculated from the append-only pipeline history.</p>
          </div>
          <form onSubmit={(event) => { event.preventDefault(); void load(); }} className="flex flex-wrap items-end gap-2 rounded-2xl border border-line bg-white/80 p-3 shadow-sm">
            <label className="text-[10px] font-bold uppercase tracking-[.13em] text-stone-500">From<input value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} type="date" className="mt-1.5 block rounded-lg border border-line bg-[#fdfbf8] px-2 py-1.5 text-xs font-normal text-ink outline-none focus:border-pine" /></label>
            <label className="text-[10px] font-bold uppercase tracking-[.13em] text-stone-500">To<input value={dateTo} onChange={(event) => setDateTo(event.target.value)} type="date" className="mt-1.5 block rounded-lg border border-line bg-[#fdfbf8] px-2 py-1.5 text-xs font-normal text-ink outline-none focus:border-pine" /></label>
            <button type="submit" disabled={loading} className="rounded-lg bg-pine px-3 py-[7px] text-xs font-semibold text-white transition hover:bg-[#0e2928] disabled:opacity-50">{loading ? "Refreshing…" : "Apply"}</button>
            {(dateFrom || dateTo) && <button type="button" onClick={() => void clearFilters()} className="px-1 text-xs font-semibold text-stone-500 hover:text-ink">Clear</button>}
          </form>
        </div>

        {error && <div className="mt-5 rounded-xl border border-[#e5bcad] bg-[#fdf0ea] px-4 py-3 text-sm text-[#8d3e2d]">Refresh failed: {error}. Existing data remains on screen.</div>}
        {data.meta.selected_row_count === 0 && <div className="mt-5 rounded-xl border border-[#e5bcad] bg-[#fdf0ea] px-4 py-3 text-sm text-[#8d3e2d]">No timestamped telemetry records match this date range.</div>}

        <div className="mt-7 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <Kpi label="Pipeline runs" value={number(data.overview.run_count)} detail={data.overview.run_status_note} accent="pine" />
          <Kpi label="Latest duration" value={duration(latest?.duration_seconds ?? null)} detail={latest ? `${dateTime(latest.timestamp)} · P95 ${duration(data.overview.duration.p95)}` : "No valid timestamp"} accent="terracotta" />
          <Kpi label="Publication yield" value={data.overview.publication_yield_percent === null ? "—" : `${number(data.overview.publication_yield_percent, 1)}%`} detail={`${number(data.overview.total_final_articles)} final from ${number(data.overview.total_scraped)} scraped`} accent="gold" />
          <Kpi label="LLM failure rate" value={data.llm.failure_rate_percent === null ? "—" : `${number(data.llm.failure_rate_percent, 1)}%`} detail={`${number(data.llm.total_failures)} failures across ${number(data.llm.total_calls)} calls`} accent="slate" />
        </div>

        <div className="mt-4 rounded-2xl border border-[#d5dfd8] bg-[#edf4ef] px-4 py-3 text-sm leading-6 text-pine sm:px-5"><span className="mr-2 font-bold">Operator note.</span>{data.overview.slowest_stage ? `${data.overview.slowest_stage.label} is the slowest measured stage at ${duration(data.overview.slowest_stage.average)} per run. ` : "No stage measurement is available. "}{data.stages.note}</div>

        <div className="mt-5 grid gap-5 xl:grid-cols-2"><DurationTrend trend={data.duration_trend} p50={data.overview.duration.p50} /><StageAverage data={data} /></div>
        <div className="mt-5 grid gap-5 xl:grid-cols-2"><ProcessFunnel data={data} /><CategoryMix data={data} /></div>
        <div className="mt-5 grid gap-5 xl:grid-cols-2"><LlmPanel data={data} /><RunBreakdown run={selectedRun} stageLabels={stageLabels} /></div>
        <div className="mt-5"><QualityPanel data={data} /></div>
        <div className="mt-5"><RunLedger data={data} selectedRunId={selectedRunId} onSelect={setSelectedRunId} /></div>

        <div className="mt-5 grid gap-5 lg:grid-cols-[1.15fr_.85fr]">
          <Card className="p-5 sm:p-6"><p className="text-[10px] font-bold uppercase tracking-[.2em] text-terracotta">Metric integrity</p><h2 className="mt-1 font-serif text-[22px] font-semibold">LLM accounting checks</h2><div className="mt-4 grid gap-4 sm:grid-cols-3"><MiniMetric label="Total tokens" value={compact(data.llm.total_tokens)} /><MiniMetric label="Tokens / response" value={number(data.llm.tokens_per_usage_response, 0)} /><MiniMetric label="Tokens / final article" value={number(data.llm.tokens_per_final_article, 0)} /></div><p className="mt-4 text-xs leading-5 text-stone-500">{data.llm.token_total_inconsistencies.length ? `${data.llm.token_total_inconsistencies.length} recorded token total(s) differ from prompt + response; source values are shown unchanged.` : "All rows with prompt, response, and total token values agree."} {data.llm.latency_percentiles_note}</p></Card>
          <Card className="p-5 sm:p-6"><p className="text-[10px] font-bold uppercase tracking-[.2em] text-terracotta">Data-source notes</p><h2 className="mt-1 font-serif text-[22px] font-semibold">Known limits</h2><ul className="mt-3 space-y-2 text-xs leading-5 text-stone-600">{data.meta.warnings.slice(0, 4).map((warning) => <li className="flex gap-2" key={warning}><span className="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full bg-terracotta" />{warning}</li>)}</ul></Card>
        </div>

        <footer className="mt-10 flex flex-col justify-between gap-2 border-t border-line pt-5 text-xs text-stone-500 sm:flex-row"><span>Source: {data.meta.source.path.split(/[\\/]/).slice(-2).join("/")} · {data.meta.source.row_count} rows · updated {dateTime(data.meta.source.last_modified)}</span><span>CSV is read only · no pipeline reports were changed</span></footer>
      </div>
    </main>
  );
}
