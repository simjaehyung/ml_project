"use client";

/**
 * 자동 유입 데모 — "신규 입력의 자동화" 라이브 데모
 * --------------------------------------------------------------------
 * 캐글 Hotel Booking 데이터(public/hub_stream.json, 25k·시간순)를 클라이언트에서
 * 재생한다. 예약이 예약일(d) 순서로 자동 유입되며(입력), 4개 비즈니스 도메인으로
 * 실시간 정리(라우팅)된다. 이후 발표자는 Hub 탭으로 넘어가 모델 진화를 본다.
 *
 * 정직 프레이밍(Hub와 동일):
 *  - 백엔드에 25k를 POST하지 않는다. risk는 최종 LightGBM 사전계산값을 '재생'할 뿐
 *    — 실시간 학습/추론 아님. 화면에 그대로 라벨.
 *  - 도메인 1(오버부킹)만 실모델. 2~4는 동일 데이터에 규칙 라우팅(확장성 데모).
 *  - 새 수치 날조 없음 — 모든 신호는 스트림의 실제 필드(risk/adr/lead/arr)에서만.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";

interface StreamRow {
  d: string;
  arr: string;
  country: string;
  channel: string;
  hotel: string;
  lead: number;
  adr: number;
  risk: number;
  canceled: number;
  color: "low" | "med" | "high";
}

type DomStatus = "live" | "rule" | "planned";
interface StreamDomain {
  n: number;
  name: string;
  color: string;
  status: DomStatus;
  inputs: string;   // 입력 신호
  criteria: string; // 판단 기준 (라우팅 규칙)
  output: string;   // 권장 출력
  route: (r: StreamRow) => boolean;
  signal: (r: StreamRow) => string;
}

// 4 판단 기준(criteria) — 스트림 필드로 실제 라우팅. criteria = 실제 사용 규칙(정직).
const STREAM_DOMAINS: StreamDomain[] = [
  { n: 1, name: "오버부킹", color: "var(--risk-high)", status: "live",
    inputs: "취소위험 · lead_time", criteria: "위험 ≥ 50%", output: "오버부킹 세그먼트 8~30%",
    route: (r) => r.risk >= 0.5, signal: (r) => `위험 ${Math.round(r.risk * 100)}%` },
  { n: 2, name: "부가 매출", color: "var(--flexi-color)", status: "rule",
    inputs: "ADR · 세그먼트", criteria: "객단가(ADR) ≥ €110", output: "객실 업그레이드 · 식음료 추가판매",
    route: (r) => r.adr >= 110, signal: (r) => `€${Math.round(r.adr)}` },
  { n: 3, name: "동적 가격", color: "#60A5FA", status: "planned",
    inputs: "lead_time · 수요", criteria: "리드타임 ≥ 90일", output: "가격 탄력 조정",
    route: (r) => r.lead >= 90, signal: (r) => `리드 ${r.lead}일` },
  { n: 4, name: "수요 · 인력", color: "#A78BFA", status: "planned",
    inputs: "계절 · 도착", criteria: "성수기(6~8월) 도착", output: "인력 배치 예측",
    route: (r) => { const m = +r.arr.slice(5, 7); return m >= 6 && m <= 8; }, signal: () => "성수기" },
];

const STATUS_LABEL: Record<DomStatus, string> = {
  live: "실모델 · LightGBM",
  rule: "규칙 기반",
  planned: "확장 설계",
};
const STATUS_COLOR: Record<DomStatus, string> = {
  live: "var(--risk-low)",      // emerald
  rule: "var(--flexi-color)",   // amber
  planned: "rgba(255,255,255,0.5)",
};
const AI_READY = "#22D3EE";     // cyan — 'AI-ready' 공통 마커
const RISK_HEX = { high: "var(--risk-high)", med: "var(--flexi-color)", low: "var(--risk-low)" } as const;
const TICK_MS = 40;
const ROWS_PER_TICK = 40; // 1× ≈ 25k / 25fps / 40 ≈ 25초 완주

function tint(c: string, p: number) { return `color-mix(in srgb, ${c} ${p}%, transparent)`; }
function fmt(n: number) { return n.toLocaleString("en-US"); }

interface Snapshot {
  collected: number; canceled: number; low: number; med: number; high: number;
  domCount: number[]; curDate: string;
}
const ZERO: Snapshot = { collected: 0, canceled: 0, low: 0, med: 0, high: 0, domCount: [0, 0, 0, 0], curDate: "" };

export default function AutoFeedDemo() {
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [snap, setSnap] = useState<Snapshot>(ZERO);
  const [recent, setRecent] = useState<StreamRow[]>([]);
  const [domRecent, setDomRecent] = useState<{ id: string; sig: string; country: string; hotel: string }[][]>([[], [], [], []]);
  const [spotlight, setSpotlight] = useState<StreamRow | null>(null);
  const [done, setDone] = useState(false);

  const dataRef = useRef<StreamRow[]>([]);
  const ptrRef = useRef(0);
  const accRef = useRef<Snapshot>({ ...ZERO, domCount: [0, 0, 0, 0] });
  const recentRef = useRef<StreamRow[]>([]);
  const domRecentRef = useRef<{ id: string; sig: string; country: string; hotel: string }[][]>([[], [], [], []]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // 데이터 로드
  useEffect(() => {
    let cancelled = false;
    fetch("/hub_stream.json")
      .then((r) => { if (!r.ok) throw new Error(`hub_stream.json ${r.status}`); return r.json(); })
      .then((j) => {
        if (cancelled) return;
        dataRef.current = (j.stream ?? []) as StreamRow[]; // 이미 d(예약일) 시간순 정렬됨
        setReady(true);
      })
      .catch((e) => { if (!cancelled) setError(e instanceof Error ? e.message : "로드 실패"); });
    return () => { cancelled = true; };
  }, []);

  const reset = useCallback(() => {
    setPlaying(false);
    setDone(false);
    ptrRef.current = 0;
    accRef.current = { collected: 0, canceled: 0, low: 0, med: 0, high: 0, domCount: [0, 0, 0, 0], curDate: "" };
    recentRef.current = [];
    domRecentRef.current = [[], [], [], []];
    setSnap(ZERO);
    setRecent([]);
    setDomRecent([[], [], [], []]);
    setSpotlight(null);
  }, []);

  // 재생 루프
  useEffect(() => {
    if (!playing) {
      if (timerRef.current) clearInterval(timerRef.current);
      timerRef.current = null;
      return;
    }
    timerRef.current = setInterval(() => {
      const data = dataRef.current;
      const acc = accRef.current;
      const batch = ROWS_PER_TICK * speed;
      let last: StreamRow | null = null;
      for (let k = 0; k < batch && ptrRef.current < data.length; k++) {
        const r = data[ptrRef.current++];
        acc.collected++;
        if (r.canceled) acc.canceled++;
        acc[r.color]++;
        acc.curDate = r.d;
        recentRef.current.unshift(r);
        if (recentRef.current.length > 8) recentRef.current.pop();
        STREAM_DOMAINS.forEach((dom, i) => {
          if (dom.route(r)) {
            acc.domCount[i]++;
            const lst = domRecentRef.current[i];
            lst.unshift({ id: `${r.country}-${r.d}-${ptrRef.current}`, sig: dom.signal(r), country: r.country, hotel: r.hotel });
            if (lst.length > 5) lst.pop();
          }
        });
        last = r;
      }
      setSnap({ ...acc, domCount: [...acc.domCount] });
      setRecent([...recentRef.current]);
      setDomRecent(domRecentRef.current.map((l) => [...l]));
      if (last) setSpotlight(last);
      if (ptrRef.current >= data.length) {
        setPlaying(false);
        setDone(true);
      }
    }, TICK_MS);
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [playing, speed]);

  const handlePlay = useCallback(() => {
    if (done || ptrRef.current >= dataRef.current.length) { reset(); setTimeout(() => setPlaying(true), 0); return; }
    setPlaying((p) => !p);
  }, [done, reset]);

  const total = dataRef.current.length || 25000;
  const pct = total ? (snap.collected / total) * 100 : 0;
  const cancelRate = snap.collected ? (snap.canceled / snap.collected) * 100 : 0;

  return (
    <div className="space-y-5 text-white">
      {/* 헤더 */}
      <div>
        <h1 className="text-xl font-semibold">자동 유입 데모 <span className="text-xs font-normal text-white/40">(신규 입력 자동화)</span></h1>
        <p className="text-xs text-white/40 mt-0.5">
          캐글 예약 데이터가 시간순으로 자동 유입되며 도메인별로 정리됩니다. → 모델 진화는 <span className="text-white/60">Hub</span> 탭에서.
        </p>
      </div>

      {error && (
        <div className="rounded-md px-4 py-2 text-sm" style={{ background: tint("var(--risk-high)", 15), border: `1px solid ${tint("var(--risk-high)", 40)}`, color: "var(--risk-high)" }}>
          데이터 로드 오류: {error} — public/hub_stream.json 확인.
        </div>
      )}

      {/* 컨트롤 바 */}
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-white/10 bg-[var(--bg-card)] px-4 py-3">
        <button
          onClick={handlePlay}
          disabled={!ready}
          className="rounded-md bg-white px-4 py-1.5 text-sm font-semibold text-black transition-opacity hover:opacity-90 disabled:opacity-40"
        >
          {playing ? "❚❚ 일시정지" : done || snap.collected >= total ? "↻ 다시재생" : "▶ 자동 유입 시작"}
        </button>
        <button onClick={reset} className="rounded-md border border-white/15 px-3 py-1.5 text-sm text-white/60 transition-colors hover:bg-white/5">
          처음으로
        </button>
        <div className="flex items-center gap-1">
          {[1, 2, 4].map((s) => (
            <button key={s} onClick={() => setSpeed(s)}
              className="rounded px-2 py-1 text-xs font-mono transition-colors"
              style={speed === s ? { background: "#fff", color: "#000" } : { color: "rgba(255,255,255,0.45)", border: "1px solid rgba(255,255,255,0.12)" }}>
              {s}×
            </button>
          ))}
        </div>
        {/* 진행 */}
        <div className="flex-1 min-w-[160px]">
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/10">
            <div className="h-full rounded-full transition-[width] duration-100" style={{ width: `${pct}%`, background: "var(--flexi-color)" }} />
          </div>
          <div className="mt-1 flex justify-between text-[10px] text-white/30">
            <span className="font-mono">{snap.curDate || "—"}</span>
            <span className="font-mono">{fmt(snap.collected)} / {fmt(total)}</span>
          </div>
        </div>
      </div>

      {/* 입력(현재 유입 + 누적) */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(280px,360px)_1fr]">
        {/* 현재 유입 스포트라이트 + 카운터 */}
        <div className="space-y-4">
          <div className="rounded-xl border border-white/10 bg-[var(--bg-card)] p-4">
            <div className="text-[10px] uppercase tracking-wider text-white/40">현재 유입 (입력)</div>
            {spotlight ? (
              <div className="mt-2">
                <div className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ background: RISK_HEX[spotlight.color] }} />
                  <span className="text-sm font-medium">{spotlight.hotel.replace(" Hotel", "")} · {spotlight.country}</span>
                  <span className="ml-auto font-mono text-sm tabular-nums" style={{ color: RISK_HEX[spotlight.color] }}>
                    위험 {Math.round(spotlight.risk * 100)}%
                  </span>
                </div>
                <div className="mt-2 grid grid-cols-3 gap-2 text-center">
                  {[["채널", spotlight.channel], ["ADR", `€${Math.round(spotlight.adr)}`], ["리드", `${spotlight.lead}일`]].map(([k, v]) => (
                    <div key={k} className="rounded-lg bg-white/[0.03] py-1.5">
                      <div className="text-[9px] text-white/35">{k}</div>
                      <div className="font-mono text-xs text-white/80 truncate px-1">{v}</div>
                    </div>
                  ))}
                </div>
                <div className="mt-1.5 text-[10px] text-white/30 font-mono">예약일 {spotlight.d} · 도착 {spotlight.arr}</div>
              </div>
            ) : (
              <div className="mt-3 text-center text-xs text-white/25">▶ 자동 유입을 시작하면 예약이 흘러듭니다</div>
            )}
          </div>

          {/* 누적 카운터 */}
          <div className="rounded-xl border border-white/10 bg-[var(--bg-card)] p-4">
            <div className="flex items-baseline justify-between">
              <div>
                <div className="text-[10px] uppercase tracking-wider text-white/40">수집 누적</div>
                <div className="font-mono text-3xl font-bold tabular-nums">{fmt(snap.collected)}</div>
              </div>
              <div className="text-right">
                <div className="text-[10px] uppercase tracking-wider text-white/40">취소율</div>
                <div className="font-mono text-xl font-bold tabular-nums" style={{ color: "var(--risk-high)" }}>{cancelRate.toFixed(1)}%</div>
              </div>
            </div>
            {/* 위험 분포 바 */}
            <div className="mt-3 flex h-2 w-full overflow-hidden rounded-full bg-white/10">
              {(["high", "med", "low"] as const).map((k) => {
                const w = snap.collected ? (snap[k] / snap.collected) * 100 : 0;
                return <div key={k} style={{ width: `${w}%`, background: RISK_HEX[k] }} />;
              })}
            </div>
            <div className="mt-1.5 flex gap-3 text-[10px] text-white/40">
              <span><span style={{ color: "var(--risk-high)" }}>●</span> 고 {fmt(snap.high)}</span>
              <span><span style={{ color: "var(--flexi-color)" }}>●</span> 중 {fmt(snap.med)}</span>
              <span><span style={{ color: "var(--risk-low)" }}>●</span> 저 {fmt(snap.low)}</span>
            </div>
          </div>

          {/* 유입 티커 */}
          <div className="rounded-xl border border-white/10 bg-[var(--bg-card)] p-4">
            <div className="text-[10px] uppercase tracking-wider text-white/40 mb-2">유입 스트림</div>
            <div className="space-y-1" style={{ minHeight: 150 }}>
              {recent.length === 0 ? (
                <div className="py-6 text-center text-[11px] text-white/20">—</div>
              ) : recent.map((r, i) => (
                <div key={`${r.d}-${r.country}-${i}`} className="flex items-center gap-2 text-[11px]" style={{ opacity: 1 - i * 0.1 }}>
                  <span className="h-1.5 w-1.5 rounded-full shrink-0" style={{ background: RISK_HEX[r.color] }} />
                  <span className="font-mono text-white/40 shrink-0">{r.d.slice(2)}</span>
                  <span className="text-white/55 shrink-0 w-8">{r.country}</span>
                  <span className="text-white/35 truncate">{r.hotel.replace(" Hotel", "")} · {r.channel}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* 정리(도메인 라우팅) */}
        <div>
          <div className="text-[10px] uppercase tracking-wider text-white/40 mb-2">도메인 정리 (라우팅)</div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {STREAM_DOMAINS.map((dom, i) => (
              <div key={dom.n} className="flex flex-col rounded-xl border border-white/10 bg-[var(--bg-card)] overflow-hidden">
                <div className="p-3" style={{ borderTop: `2px solid ${dom.color}` }}>
                  <div className="flex items-start justify-between gap-1">
                    <div className="flex items-center gap-1.5 min-w-0">
                      <span className="font-mono text-[10px] text-white/35">D{dom.n}</span>
                      <h3 className="text-[13px] font-semibold truncate">{dom.name}</h3>
                    </div>
                    <div className="text-right shrink-0">
                      <span className="font-mono text-xl font-bold tabular-nums leading-none" style={{ color: dom.color }}>{fmt(snap.domCount[i])}</span>
                      <div className="text-[8px] text-white/30">실시간 라우팅</div>
                    </div>
                  </div>
                  {/* 성숙도 + AI-ready 배지 */}
                  <div className="mt-1.5 flex flex-wrap gap-1">
                    <span className="rounded border px-1 py-0.5 text-[8.5px] font-medium"
                      style={{ background: tint(STATUS_COLOR[dom.status], 13), color: STATUS_COLOR[dom.status], borderColor: tint(STATUS_COLOR[dom.status], 30) }}>
                      {STATUS_LABEL[dom.status]}
                    </span>
                    <span className="rounded border px-1 py-0.5 text-[8.5px] font-medium"
                      style={{ background: tint(AI_READY, 12), color: AI_READY, borderColor: tint(AI_READY, 28) }}>
                      AI-ready
                    </span>
                  </div>
                  {/* 판단 기준: 입력 → 기준 → 권장 */}
                  <dl className="mt-2 space-y-0.5 text-[9px] leading-snug">
                    <div className="flex gap-1.5"><dt className="w-6 shrink-0 text-white/30">입력</dt><dd className="flex-1 text-white/55">{dom.inputs}</dd></div>
                    <div className="flex gap-1.5"><dt className="w-6 shrink-0 text-white/30">기준</dt><dd className="flex-1 text-white/55">{dom.criteria}</dd></div>
                    <div className="flex gap-1.5"><dt className="w-6 shrink-0 text-white/30">권장</dt><dd className="flex-1" style={{ color: dom.color }}>{dom.output}</dd></div>
                  </dl>
                </div>
                <div className="flex-1 p-1.5 space-y-1" style={{ minHeight: 150 }}>
                  {domRecent[i].length === 0 ? (
                    <div className="py-6 text-center text-[10px] text-white/20">—</div>
                  ) : domRecent[i].map((it, k) => (
                    <div key={it.id} className="rounded-md px-2 py-1.5 text-[10px]" style={{ background: "rgba(255,255,255,0.02)", borderLeft: `2px solid ${dom.color}`, opacity: 1 - k * 0.13 }}>
                      <div className="flex items-center gap-1">
                        <span className="text-white/55">{it.country}</span>
                        <span className="ml-auto font-mono tabular-nums" style={{ color: dom.color }}>{it.sig}</span>
                      </div>
                      <div className="text-white/30">{it.hotel.replace(" Hotel", "")}</div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 정직성 + Hub 전환 */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-white/10 bg-white/[0.015] px-4 py-3">
        <p className="text-[11px] leading-relaxed text-white/45 max-w-3xl">
          <span className="text-white/65 font-medium">정직성 ·</span>{" "}
          캐글 Hotel Booking 데이터(전체 119,390건의 25k 시간순 샘플)를 <span className="text-white/65">재생</span>합니다. risk는 최종 LightGBM
          <span className="text-white/65"> 사전계산값</span> — 실시간 학습/추론이 아닙니다. 도메인 1만 실모델, 2~4는 규칙 라우팅(확장성 데모).
        </p>
        <Link href="/dashboard/hub"
          className="shrink-0 rounded-lg px-3 py-2 text-xs font-semibold text-black transition-opacity hover:opacity-90"
          style={{ background: "var(--flexi-color)" }}>
          다음 → Hub에서 모델 진화 보기
        </Link>
      </div>
    </div>
  );
}
