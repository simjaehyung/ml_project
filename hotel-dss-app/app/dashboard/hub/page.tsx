"use client";

/**
 * HUB — Reservation Intake Stream + Growth Curve
 * ------------------------------------------------
 * 최종발표(2026-06-10) 핵심 스토리: "예약 데이터가 시간순으로 흘러들수록 모델이 자란다."
 * 좌: 예약 유입 스트림(누적 카운터 + 최근 카드).  우: 주차별 PR-AUC 성장곡선(재생커서 동기).
 * 클라이맥스 = wk≈84 / n≈53,615(5.4만)에서 LightGBM이 LR 추월 → full 0.820.
 *
 * [설계 메모 — handoff_dss_demo.md와의 의도적 차이]
 *   handoff는 "stream을 d(예약일) 순서로 재생"이라 했으나, growth_curve_agg.csv의
 *   cutoff_week 및 hub_stream.json의 wk는 **도착주차(arrival week)** 기준이다.
 *   (검증: arr 정렬 시 wk inversion 0 / train=wk≤106 16,484건 = test split 경계와 일치.)
 *   곡선 커서가 단조 증가하며 "≤W까지 모인 데이터로 학습한 성능"과 정확히 맞물리도록
 *   재생을 wk 순서로 한다. 정직성 각주(사전계산 risk / 25k 다운샘플)는 그대로 유지.
 *
 * 데이터: public/hub_stream.json (25k, meta+stream) · public/hub_growth.json (cumulative window)
 * 성능: 25k DOM 동시 렌더 금지(최근 ~36장만) · 누적은 카운터/분포바 · 곡선 path 1회 계산 후 clip 폭만 이동.
 */

import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import Link from "next/link";

// ── 덱 팔레트(에디토리얼/인스트루먼트, dss_story_demo.html 기준) ──────────────
const C = {
  indigo: "#1B3A8F",
  indigoDeep: "#13245A",
  amber: "#8A5A0F",
  brick: "#B23A2E", // risk high
  ochre: "#B8862B", // risk med
  forest: "#3F7A52", // risk low
  ink: "#15171C",
  inkSoft: "#3A3F4A",
  muted: "#7C7768",
  line: "#D7D3C8",
  lineSoft: "#E7E3D8",
  paper: "#F4F1E8",
  paper2: "#EDE9DC",
  card: "#FBFAF4",
} as const;

const RISK_COLOR: Record<string, string> = {
  high: C.brick,
  med: C.ochre,
  low: C.forest,
};

// 곡선에 그릴 모델 (발표 기본 3개 + 옵션 2개)
const LINE_MODELS = [
  { key: "LightGBM", color: C.indigo, width: 2.6, dash: "", label: "LightGBM" },
  { key: "Logistic Regression", color: C.amber, width: 2.0, dash: "", label: "Logistic" },
  { key: "Dummy", color: C.muted, width: 1.4, dash: "4 4", label: "Dummy" },
] as const;
const OPTIONAL_MODELS = [
  { key: "XGBoost", color: C.forest, width: 1.6, dash: "2 3", label: "XGBoost" },
  { key: "Random Forest", color: C.brick, width: 1.4, dash: "2 3", label: "Random Forest" },
] as const;

// 재학습 현황 패널: 5개 모델 전체에서 "현재 채택(최고 PR-AUC)" 모델을 고른다.
const ALL_MODEL_KEYS = ["Dummy", "Logistic Regression", "Random Forest", "XGBoost", "LightGBM"] as const;
const MODEL_SHORT: Record<string, string> = {
  "Dummy": "Dummy",
  "Logistic Regression": "Logistic Reg.",
  "Random Forest": "Random Forest",
  "XGBoost": "XGBoost",
  "LightGBM": "LightGBM",
};
const MODEL_COLOR: Record<string, string> = {
  "Dummy": C.muted,
  "Logistic Regression": C.amber,
  "Random Forest": C.brick,
  "XGBoost": C.forest,
  "LightGBM": C.indigo,
};
const PR_BASELINE = 0.387; // Dummy 바닥 (전 구간 고정)

// ── 데이터 타입 ──────────────────────────────────────────────────────────────
interface StreamRow {
  d: string;
  arr: string;
  wk: number;
  country: string;
  channel: string;
  hotel: string;
  lead: number;
  adr: number;
  risk: number;
  canceled: number;
  split: "train" | "test";
  color: "low" | "med" | "high";
}
interface StreamMeta {
  disclaimer?: string;
  n_full?: number;
  n_sample?: number;
}
interface GrowthPoint {
  wk: number;
  n: number;
  pr_auc: number;
}
interface GrowthSeries {
  model: string;
  points: GrowthPoint[];
}

// ── 곡선 좌표계 ──────────────────────────────────────────────────────────────
const VB_W = 760;
const VB_H = 420;
const PAD = { t: 28, r: 86, b: 40, l: 52 };
const WK_MIN = 28; // 곡선 정의 구간 (cumulative cutoff_week)
const WK_MAX = 106;
const Y_MIN = 0.35;
const Y_MAX = 0.83;
const CROSSOVER_WK = 84;

function xScale(wk: number): number {
  const c = Math.max(WK_MIN, Math.min(WK_MAX, wk));
  return PAD.l + ((c - WK_MIN) / (WK_MAX - WK_MIN)) * (VB_W - PAD.l - PAD.r);
}
function yScale(v: number): number {
  const c = Math.max(Y_MIN, Math.min(Y_MAX, v));
  return VB_H - PAD.b - ((c - Y_MIN) / (Y_MAX - Y_MIN)) * (VB_H - PAD.t - PAD.b);
}

// 스트림 wk(27~141) → 재생 진행률 0~1
const PLAY_WK_MIN = 27;
const PLAY_WK_MAX = 141;

function fmt(n: number): string {
  return n.toLocaleString("en-US");
}

export default function HubPage() {
  const [meta, setMeta] = useState<StreamMeta>({});
  const [growth, setGrowth] = useState<GrowthSeries[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  // 재생 상태 (렌더용)
  const [cursorWk, setCursorWk] = useState(PLAY_WK_MIN);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [showOptional, setShowOptional] = useState(false);
  const [capture, setCapture] = useState(false);

  // 누적 카운터 (렌더용)
  const [counts, setCounts] = useState({
    collected: 0,
    canceled: 0,
    low: 0,
    med: 0,
    high: 0,
    train: 0,
    test: 0,
    curDate: "",
    curN: 0,
  });
  const [recent, setRecent] = useState<StreamRow[]>([]);

  // 애니메이션용 ref (리렌더 없이 유지)
  const sortedRef = useRef<StreamRow[]>([]);
  const ptrRef = useRef(0);
  const accRef = useRef({ collected: 0, canceled: 0, low: 0, med: 0, high: 0, train: 0, test: 0, curDate: "", curN: 0 });
  const recentRef = useRef<StreamRow[]>([]);
  const cursorRef = useRef(PLAY_WK_MIN);
  const rafRef = useRef<number | null>(null);
  const lastTsRef = useRef<number | null>(null);
  const frameCounter = useRef(0);

  // n_train 룩업 (wk → LightGBM n_train, 카운터 정합용으로는 실제 스트림 누적 사용)
  // 곡선값 룩업: model → (wk → pr_auc), wk≤cursor 중 최대 wk값
  const valueAt = useCallback(
    (model: string, wk: number): { pr: number; n: number } | null => {
      const s = growth.find((g) => g.model === model);
      if (!s) return null;
      let best: GrowthPoint | null = null;
      for (const p of s.points) {
        if (p.wk <= wk && (!best || p.wk > best.wk)) best = p;
      }
      return best ? { pr: best.pr_auc, n: best.n } : null;
    },
    [growth]
  );

  // ── 데이터 로드 ──
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [sRes, gRes] = await Promise.all([
          fetch("/hub_stream.json"),
          fetch("/hub_growth.json"),
        ]);
        if (!sRes.ok || !gRes.ok) throw new Error(`fetch 실패 (stream ${sRes.status} / growth ${gRes.status})`);
        const sJson = await sRes.json();
        const gJson = await gRes.json();
        if (cancelled) return;
        const stream: StreamRow[] = sJson.stream ?? [];
        // wk(도착주차) 안정 정렬 → 곡선 커서 단조 증가 보장
        const sorted = [...stream].sort((a, b) => a.wk - b.wk);
        sortedRef.current = sorted;
        setMeta(sJson.meta ?? {});
        setGrowth(gJson.series ?? []);
        setReady(true);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "데이터 로드 실패");
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  // ── 카운터를 특정 주차까지 동기 재계산 (seek/restart용) ──
  const rebuildTo = useCallback((targetWk: number) => {
    const sorted = sortedRef.current;
    const acc = { collected: 0, canceled: 0, low: 0, med: 0, high: 0, train: 0, test: 0, curDate: "", curN: 0 };
    const ring: StreamRow[] = [];
    let i = 0;
    for (; i < sorted.length; i++) {
      const r = sorted[i];
      if (r.wk > targetWk) break;
      acc.collected++;
      if (r.canceled) acc.canceled++;
      acc[r.color]++;
      acc[r.split]++;
      acc.curDate = r.arr;
      ring.push(r);
      if (ring.length > 36) ring.shift();
    }
    acc.curN = acc.collected;
    ptrRef.current = i;
    accRef.current = acc;
    recentRef.current = ring;
    cursorRef.current = targetWk;
    setCounts({ ...acc });
    setRecent([...ring]);
    setCursorWk(targetWk);
  }, []);

  // ── RAF 재생 루프 ──
  useEffect(() => {
    if (!playing) {
      if (rafRef.current != null) cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
      lastTsRef.current = null;
      return;
    }
    const WEEKS_PER_SEC = 1.0; // 기본 ≈ (141-27)/1.0 ≈ 114s 완주 (speed=1)
    function tick(ts: number) {
      if (lastTsRef.current == null) lastTsRef.current = ts;
      const dt = (ts - lastTsRef.current) / 1000;
      lastTsRef.current = ts;

      let cur = cursorRef.current + WEEKS_PER_SEC * speed * dt;
      if (cur >= PLAY_WK_MAX) {
        cur = PLAY_WK_MAX;
      }
      cursorRef.current = cur;

      const sorted = sortedRef.current;
      const acc = accRef.current;
      let advanced = false;
      while (ptrRef.current < sorted.length && sorted[ptrRef.current].wk <= cur) {
        const r = sorted[ptrRef.current];
        acc.collected++;
        if (r.canceled) acc.canceled++;
        acc[r.color]++;
        acc[r.split]++;
        acc.curDate = r.arr;
        recentRef.current.push(r);
        if (recentRef.current.length > 36) recentRef.current.shift();
        ptrRef.current++;
        advanced = true;
      }
      acc.curN = acc.collected;

      // 배치 flush — 매 프레임 대신 4프레임 또는 신규유입 있을 때
      frameCounter.current++;
      if (advanced || frameCounter.current % 4 === 0) {
        setCounts({ ...acc });
        setRecent([...recentRef.current]);
        setCursorWk(cur);
      }

      if (cur >= PLAY_WK_MAX) {
        setPlaying(false);
        setCounts({ ...acc });
        setRecent([...recentRef.current]);
        setCursorWk(PLAY_WK_MAX);
        return;
      }
      rafRef.current = requestAnimationFrame(tick);
    }
    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current != null) cancelAnimationFrame(rafRef.current);
    };
  }, [playing, speed]);

  // ── 컨트롤 ──
  const handlePlayPause = useCallback(() => {
    if (cursorRef.current >= PLAY_WK_MAX) {
      // 끝났으면 처음부터
      rebuildTo(PLAY_WK_MIN);
      setPlaying(true);
    } else {
      setPlaying((p) => !p);
    }
  }, [rebuildTo]);

  const handleSeek = useCallback(
    (wk: number) => {
      setPlaying(false);
      const w = Math.max(PLAY_WK_MIN, Math.min(PLAY_WK_MAX, wk));
      rebuildTo(w);
    },
    [rebuildTo]
  );

  const handleRestart = useCallback(() => {
    setPlaying(false);
    rebuildTo(PLAY_WK_MIN);
  }, [rebuildTo]);

  // 키보드: space=재생/정지, c=캡쳐모드, f=풀스크린, r=리셋, 1/2/3/4=속도
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement) return;
      if (e.code === "Space") {
        e.preventDefault();
        handlePlayPause();
      } else if (e.key === "c") {
        setCapture((v) => !v);
      } else if (e.key === "f") {
        if (!document.fullscreenElement) document.documentElement.requestFullscreen?.();
        else document.exitFullscreen?.();
      } else if (e.key === "r") {
        handleRestart();
      } else if (["1", "2", "3", "4"].includes(e.key)) {
        setSpeed([0.5, 1, 2, 4][Number(e.key) - 1]);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [handlePlayPause, handleRestart]);

  // ?capture=1 초기 진입
  useEffect(() => {
    if (typeof window !== "undefined" && new URLSearchParams(window.location.search).get("capture") === "1") {
      setCapture(true);
    }
  }, []);

  // ── 곡선 path (1회 계산) ──
  const paths = useMemo(() => {
    const models = showOptional ? [...LINE_MODELS, ...OPTIONAL_MODELS] : LINE_MODELS;
    return models.map((m) => {
      const s = growth.find((g) => g.model === m.key);
      const pts = (s?.points ?? []).filter((p) => p.wk >= WK_MIN && p.wk <= WK_MAX);
      const d = pts.map((p, i) => `${i === 0 ? "M" : "L"}${xScale(p.wk).toFixed(1)},${yScale(p.pr_auc).toFixed(1)}`).join(" ");
      return { ...m, d };
    });
  }, [growth, showOptional]);

  // ── 재학습 현황 (재생 동기 · hub_growth.json 사전계산값에서 파생, 런타임 학습 없음) ──
  const retrain = useMemo(() => {
    const wkc = Math.min(WK_MAX, Math.max(WK_MIN, cursorWk));
    let best: { model: string; pr: number; n: number } | null = null;
    for (const k of ALL_MODEL_KEYS) {
      const v = valueAt(k, wkc);
      if (!v) continue;
      if (!best || v.pr > best.pr) best = { model: k, pr: v.pr, n: v.n };
    }
    // 각 성장곡선 포인트 = 누적 데이터로 다시 학습한 "재학습 체크포인트"(walk-forward).
    const lg = growth.find((g) => g.model === "LightGBM");
    const pts = (lg?.points ?? []).filter((p) => p.wk >= WK_MIN && p.wk <= wkc);
    // 채택 모델 = LightGBM(최종 동결 모델, model_final.pkl). 선두 = 5개 중 argmax(정직한 경쟁).
    const lgbm = valueAt("LightGBM", wkc);
    const lgbmPr = lgbm?.pr ?? 0;
    return {
      started: cursorWk >= WK_MIN,
      lgbmPr,
      delta: lgbmPr - PR_BASELINE,
      leaderModel: best?.model ?? "Dummy",
      leaderPr: best?.pr ?? 0,
      checkpoints: pts.length,
      lastWk: pts.length ? pts[pts.length - 1].wk : WK_MIN,
      full: cursorWk >= WK_MAX,
    };
  }, [growth, cursorWk, valueAt]);

  const revealW = xScale(cursorWk) - PAD.l;
  const curClamped = Math.max(WK_MIN, Math.min(WK_MAX, cursorWk));
  const showCursorLine = cursorWk >= WK_MIN && cursorWk <= WK_MAX;
  const pastCrossover = cursorWk >= CROSSOVER_WK;
  const trainingDone = cursorWk >= WK_MAX;

  const pct = ((cursorWk - PLAY_WK_MIN) / (PLAY_WK_MAX - PLAY_WK_MIN)) * 100;

  if (error) {
    return (
      <div className="min-h-full p-8" style={{ background: C.paper, color: C.ink }}>
        <h1 className="text-lg font-semibold">HUB — 데이터 로드 오류</h1>
        <p className="mt-2 text-sm" style={{ color: C.brick }}>{error}</p>
        <p className="mt-1 text-xs" style={{ color: C.muted }}>
          public/hub_stream.json · public/hub_growth.json 존재 여부를 확인하세요.
        </p>
      </div>
    );
  }

  return (
    <div
      className="min-h-full select-none"
      style={{ background: C.paper, color: C.ink, fontFamily: '"Helvetica Neue", Arial, "Noto Sans KR", sans-serif' }}
    >
      {/* ── 페이지 헤더 (앱 컨벤션: h1 + 부제 · 캡쳐 모드에서 숨김) ── */}
      {!capture && (
        <div className="px-6 pt-5 pb-3" style={{ background: C.paper }}>
          <h1 className="text-lg font-semibold tracking-tight" style={{ color: C.ink }}>
            Hub — 데이터 수집 → 모델 성장
          </h1>
          <p className="mt-0.5 text-xs" style={{ color: C.muted }}>
            예약 데이터가 시간순으로 유입될수록 모델 성능(PR-AUC)이 자랍니다 · Dummy 0.387 → LightGBM 0.820
          </p>
        </div>
      )}

      {/* ── 컨트롤 바 (캡쳐 모드에서 숨김) ── */}
      {!capture && (
        <div
          className="flex items-center gap-3 px-6 py-3 border-y"
          style={{ borderColor: C.line, background: C.card }}
        >
          <button
            onClick={handlePlayPause}
            className="flex items-center justify-center rounded-md text-white text-sm font-medium px-4 py-1.5 transition-opacity hover:opacity-90"
            style={{ background: C.indigo }}
          >
            {playing ? "❚❚ 일시정지" : cursorWk >= PLAY_WK_MAX ? "↻ 다시재생" : "▶ 재생"}
          </button>
          <button
            onClick={handleRestart}
            className="rounded-md border px-3 py-1.5 text-sm transition-colors hover:bg-black/[0.03]"
            style={{ borderColor: C.line, color: C.inkSoft }}
          >
            처음으로
          </button>

          {/* 속도 */}
          <div className="flex items-center gap-1 ml-1">
            {[0.5, 1, 2, 4].map((s) => (
              <button
                key={s}
                onClick={() => setSpeed(s)}
                className="rounded px-2 py-1 text-xs font-mono transition-colors"
                style={
                  speed === s
                    ? { background: C.indigo, color: "#fff" }
                    : { color: C.muted, border: `1px solid ${C.lineSoft}` }
                }
              >
                {s}×
              </button>
            ))}
          </div>

          {/* seek */}
          <div className="flex items-center gap-2 flex-1 ml-2">
            <span className="text-xs font-mono shrink-0" style={{ color: C.muted }}>
              wk
            </span>
            <input
              type="range"
              min={PLAY_WK_MIN}
              max={PLAY_WK_MAX}
              step={1}
              value={Math.round(cursorWk)}
              onChange={(e) => handleSeek(Number(e.target.value))}
              className="flex-1 accent-[#1B3A8F]"
            />
            <input
              type="number"
              min={PLAY_WK_MIN}
              max={PLAY_WK_MAX}
              value={Math.round(cursorWk)}
              onChange={(e) => handleSeek(Number(e.target.value))}
              className="w-16 rounded border px-2 py-1 text-xs font-mono"
              style={{ borderColor: C.line, background: C.paper, color: C.ink }}
            />
          </div>

          <label className="flex items-center gap-1.5 text-xs" style={{ color: C.muted }}>
            <input type="checkbox" checked={showOptional} onChange={(e) => setShowOptional(e.target.checked)} />
            XGB·RF
          </label>

          <button
            onClick={() => setCapture(true)}
            className="rounded-md border px-3 py-1.5 text-xs transition-colors hover:bg-black/[0.03]"
            style={{ borderColor: C.line, color: C.inkSoft }}
            title="c: 캡쳐모드 · f: 풀스크린"
          >
            캡쳐모드 (c)
          </button>
          <Link
            href="/dashboard"
            className="text-xs transition-colors hover:underline"
            style={{ color: C.muted }}
          >
            ← Dashboard
          </Link>
        </div>
      )}

      {capture && (
        <button
          onClick={() => setCapture(false)}
          className="fixed top-3 right-3 z-50 rounded px-2 py-1 text-[10px] opacity-20 hover:opacity-80"
          style={{ background: C.ink, color: "#fff" }}
        >
          exit (c)
        </button>
      )}

      {/* ── 본문 ── */}
      <div className="grid grid-cols-[minmax(360px,5fr)_7fr] gap-px" style={{ background: C.line }}>
        {/* ── 좌: 유입 스트림 ── */}
        <div className="p-6" style={{ background: C.paper }}>
          <div className="flex items-baseline justify-between">
            <h2 className="text-sm font-semibold tracking-tight" style={{ color: C.ink }}>
              RESERVATION INTAKE
            </h2>
            <span className="font-mono text-xs" style={{ color: C.muted }}>
              cursor · {counts.curDate || "—"}
            </span>
          </div>
          <p className="mt-0.5 text-xs" style={{ color: C.muted }}>
            도착주차 순으로 예약이 유입됩니다 (한 카드 = 예약 1건)
          </p>

          {/* 누적 카운터 */}
          <div className="mt-5 grid grid-cols-2 gap-x-6 gap-y-3">
            <Stat label="수집 누적" value={fmt(counts.collected)} accent={C.indigo} big />
            <Stat
              label="취소"
              value={fmt(counts.canceled)}
              sub={counts.collected ? `${((counts.canceled / counts.collected) * 100).toFixed(1)}%` : ""}
              accent={C.brick}
              big
            />
          </div>

          {/* 현재 주차 / n_train */}
          <div className="mt-4 flex items-center gap-4 rounded-lg px-4 py-3" style={{ background: C.card, border: `1px solid ${C.lineSoft}` }}>
            <div>
              <div className="text-[10px] uppercase tracking-wide" style={{ color: C.muted }}>도착주차</div>
              <div className="font-mono text-2xl font-semibold tabular-nums" style={{ color: C.ink }}>
                {Math.round(cursorWk)}
                <span className="text-sm" style={{ color: C.muted }}>주</span>
              </div>
            </div>
            <div className="h-8 w-px" style={{ background: C.line }} />
            <div>
              <div className="text-[10px] uppercase tracking-wide" style={{ color: C.muted }}>학습 데이터(train)</div>
              <div className="font-mono text-2xl font-semibold tabular-nums" style={{ color: C.indigo }}>
                {fmt(counts.train)}
              </div>
            </div>
          </div>

          {/* 위험 분포 바 */}
          <div className="mt-4">
            <div className="text-[10px] uppercase tracking-wide mb-1.5" style={{ color: C.muted }}>
              위험 분포 (모델 사전계산)
            </div>
            <div className="flex h-3 w-full overflow-hidden rounded-full" style={{ background: C.lineSoft }}>
              {(["high", "med", "low"] as const).map((k) => {
                const v = counts[k];
                const w = counts.collected ? (v / counts.collected) * 100 : 0;
                return <div key={k} style={{ width: `${w}%`, background: RISK_COLOR[k] }} title={`${k}: ${v}`} />;
              })}
            </div>
            <div className="mt-1.5 flex gap-4 text-[11px]" style={{ color: C.inkSoft }}>
              <Legend color={C.brick} label="고위험" v={counts.high} />
              <Legend color={C.ochre} label="중위험" v={counts.med} />
              <Legend color={C.forest} label="저위험" v={counts.low} />
            </div>
          </div>

          {/* 최근 유입 카드 */}
          <div className="mt-5">
            <div className="text-[10px] uppercase tracking-wide mb-2" style={{ color: C.muted }}>
              최근 유입 ({recent.length})
            </div>
            <div className="flex flex-col gap-1" style={{ maxHeight: 280, overflow: "hidden" }}>
              {[...recent].reverse().map((r, i) => (
                <div
                  key={`${r.arr}-${r.country}-${ptrRef.current}-${i}`}
                  className="flex items-center gap-2 rounded-md px-2.5 py-1.5 text-xs"
                  style={{
                    background: r.split === "test" ? "transparent" : C.card,
                    borderLeft: `3px solid ${RISK_COLOR[r.color]}`,
                    border: `1px solid ${C.lineSoft}`,
                    borderLeftWidth: 3,
                    opacity: i > 10 ? Math.max(0.25, 1 - (i - 10) * 0.06) : 1,
                    backgroundImage:
                      r.split === "test"
                        ? `repeating-linear-gradient(45deg, transparent, transparent 5px, ${C.lineSoft} 5px, ${C.lineSoft} 6px)`
                        : undefined,
                  }}
                >
                  <span className="font-mono tabular-nums shrink-0" style={{ color: C.muted, width: 64 }}>
                    {r.arr.slice(2)}
                  </span>
                  <span className="shrink-0" style={{ color: C.inkSoft, width: 30 }}>{r.country}</span>
                  <span className="truncate flex-1" style={{ color: C.muted }}>
                    {r.hotel.replace(" Hotel", "")} · {r.channel}
                  </span>
                  <span className="font-mono tabular-nums shrink-0" style={{ color: RISK_COLOR[r.color], width: 38, textAlign: "right" }}>
                    {(r.risk * 100).toFixed(0)}%
                  </span>
                  {r.split === "test" && (
                    <span className="shrink-0 rounded px-1 text-[9px]" style={{ background: C.ink, color: C.paper }}>
                      test
                    </span>
                  )}
                </div>
              ))}
              {recent.length === 0 && (
                <div className="py-8 text-center text-xs" style={{ color: C.muted }}>
                  ▶ 재생을 누르면 예약이 흘러들기 시작합니다
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ── 우: 성장곡선 ── */}
        <div className="p-6 flex flex-col" style={{ background: C.paper }}>
          <div className="flex items-baseline justify-between">
            <h2 className="text-sm font-semibold tracking-tight" style={{ color: C.ink }}>
              GROWTH CURVE — PR-AUC vs 도착주차
            </h2>
            <span className="font-mono text-xs" style={{ color: C.muted }}>
              {trainingDone ? "학습 완료 (full)" : `학습 ≤ wk ${Math.round(curClamped)}`}
            </span>
          </div>
          <p className="mt-0.5 text-xs" style={{ color: C.muted }}>
            ≤W까지 모인 데이터로 학습한 모델의 고정 평가셋 성능 · 누적(cumulative)
          </p>

          <div className="mt-2 grid grid-cols-[1fr_minmax(196px,228px)] gap-4 flex-1 min-h-0">
            <div className="flex min-w-0 flex-col">
              <div className="relative flex-1">
            <svg viewBox={`0 0 ${VB_W} ${VB_H}`} className="w-full h-auto" style={{ maxHeight: 460 }}>
              <defs>
                <clipPath id="hub-reveal">
                  <rect x={PAD.l} y={0} width={Math.max(0, revealW)} height={VB_H} />
                </clipPath>
              </defs>

              {/* y 그리드 + 라벨 */}
              {[0.4, 0.5, 0.6, 0.7, 0.8].map((v) => (
                <g key={v}>
                  <line x1={PAD.l} y1={yScale(v)} x2={VB_W - PAD.r} y2={yScale(v)} stroke={C.lineSoft} strokeWidth={1} />
                  <text x={PAD.l - 8} y={yScale(v) + 3} textAnchor="end" fontSize={10} fill={C.muted} fontFamily="monospace">
                    {v.toFixed(1)}
                  </text>
                </g>
              ))}
              {/* x 라벨 */}
              {[28, 53, 84, 106].map((w) => (
                <text key={w} x={xScale(w)} y={VB_H - PAD.b + 16} textAnchor="middle" fontSize={10} fill={C.muted} fontFamily="monospace">
                  {w}
                </text>
              ))}
              <text x={(PAD.l + VB_W - PAD.r) / 2} y={VB_H - 4} textAnchor="middle" fontSize={10} fill={C.muted}>
                도착주차 (cutoff week)
              </text>

              {/* 전환점 W 표시 */}
              <line
                x1={xScale(CROSSOVER_WK)}
                y1={PAD.t}
                x2={xScale(CROSSOVER_WK)}
                y2={VB_H - PAD.b}
                stroke={C.amber}
                strokeWidth={pastCrossover ? 1.5 : 1}
                strokeDasharray="3 3"
                opacity={pastCrossover ? 0.9 : 0.35}
              />
              {pastCrossover && (
                <g>
                  <circle cx={xScale(CROSSOVER_WK)} cy={yScale(0.79)} r={16} fill={C.amber} opacity={0.12} />
                  <text x={xScale(CROSSOVER_WK)} y={PAD.t - 8} textAnchor="middle" fontSize={11} fontWeight={700} fill={C.amber}>
                    W ≈ 5.4만 · 84주
                  </text>
                </g>
              )}

              {/* 곡선 (clip으로 좌→우 reveal) */}
              <g clipPath="url(#hub-reveal)">
                {paths.map((p) => (
                  <path key={p.key} d={p.d} fill="none" stroke={p.color} strokeWidth={p.width} strokeDasharray={p.dash} strokeLinecap="round" strokeLinejoin="round" />
                ))}
              </g>

              {/* 현재값 점 */}
              {(showOptional ? [...LINE_MODELS, ...OPTIONAL_MODELS] : LINE_MODELS).map((m) => {
                if (cursorWk < WK_MIN) return null;
                const v = valueAt(m.key, curClamped);
                if (!v) return null;
                return <circle key={m.key} cx={xScale(curClamped)} cy={yScale(v.pr)} r={3.5} fill={m.color} stroke={C.paper} strokeWidth={1.5} />;
              })}

              {/* 재생 커서 */}
              {showCursorLine && (
                <line x1={xScale(curClamped)} y1={PAD.t} x2={xScale(curClamped)} y2={VB_H - PAD.b} stroke={C.ink} strokeWidth={1} opacity={0.5} />
              )}

              {/* full 라벨 (학습완료 시 라인 끝 값 고정) */}
              {trainingDone &&
                (showOptional ? [...LINE_MODELS, ...OPTIONAL_MODELS] : LINE_MODELS).map((m) => {
                  const v = valueAt(m.key, WK_MAX);
                  if (!v) return null;
                  return (
                    <text key={m.key} x={VB_W - PAD.r + 6} y={yScale(v.pr) + 3} fontSize={11} fontWeight={m.key === "LightGBM" ? 700 : 500} fill={m.color} fontFamily="monospace">
                      {v.pr.toFixed(3)}
                    </text>
                  );
                })}
            </svg>
          </div>

          {/* 범례 */}
          <div className="mt-1 flex flex-wrap gap-x-5 gap-y-1">
            {(showOptional ? [...LINE_MODELS, ...OPTIONAL_MODELS] : LINE_MODELS).map((m) => {
              const v = valueAt(m.key, curClamped);
              return (
                <span key={m.key} className="flex items-center gap-1.5 text-[11px]" style={{ color: C.inkSoft }}>
                  <span style={{ width: 14, height: 0, borderTop: `2px ${m.dash ? "dashed" : "solid"} ${m.color}`, display: "inline-block" }} />
                  {m.label}
                  {v && <span className="font-mono tabular-nums" style={{ color: m.color }}>{v.pr.toFixed(3)}</span>}
                </span>
              );
            })}
          </div>
            </div>
            {/* ── 재학습 현황 패널 (재생 동기 · hub_growth.json 사전계산값에서 파생) ── */}
            <RetrainPanel retrain={retrain} curDate={counts.curDate} trainCount={counts.train} pastCrossover={pastCrossover} />
          </div>
        </div>
      </div>

      {/* ── 진행바 ── */}
      <div className="h-1 w-full" style={{ background: C.lineSoft }}>
        <div className="h-full transition-[width] duration-100" style={{ width: `${pct}%`, background: pastCrossover ? C.amber : C.indigo }} />
      </div>

      {/* ── 각주 (정직성 — 캡쳐 모드에서도 유지) ── */}
      <div className="px-6 py-2.5 text-[10px] leading-relaxed" style={{ background: C.card, color: C.muted, borderTop: `1px solid ${C.line}` }}>
        ⓘ {meta.disclaimer || "risk는 최종 LightGBM 모델로 사전 계산(point-in-time 재현 아님). 수집 시연용."}
        {" · "}
        hub는 {fmt(meta.n_sample ?? 25000)}건 다운샘플 (전체 n_full {fmt(meta.n_full ?? 119390)}).
        split=='test'(2017-03~08, wk107~)은 수집되나 고정 평가셋이라 학습 제외 — 카드에 해치·`test` 태그로 구분.
        {!ready && " · 데이터 로딩 중…"}
      </div>
    </div>
  );
}

// ── 작은 컴포넌트 ──────────────────────────────────────────────────────────
function Stat({ label, value, sub, accent, big }: { label: string; value: string; sub?: string; accent: string; big?: boolean }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wide" style={{ color: C.muted }}>{label}</div>
      <div className={`font-mono font-semibold tabular-nums ${big ? "text-3xl" : "text-xl"}`} style={{ color: accent }}>
        {value}
        {sub && <span className="ml-1.5 text-xs" style={{ color: C.muted }}>{sub}</span>}
      </div>
    </div>
  );
}

function Legend({ color, label, v }: { color: string; label: string; v: number }) {
  return (
    <span className="flex items-center gap-1">
      <span className="inline-block h-2 w-2 rounded-full" style={{ background: color }} />
      {label} <span className="font-mono tabular-nums" style={{ color: C.inkSoft }}>{v.toLocaleString()}</span>
    </span>
  );
}

// ── 재학습 현황 패널 ────────────────────────────────────────────────────────
// 모든 수치는 hub_growth.json 사전계산값에서 파생된다 (런타임 학습 없음).
// "데이터가 쌓일 때마다 모델을 재학습한 결과"를 정직하게 시각화하는 것이 목적.
interface RetrainState {
  started: boolean;
  lgbmPr: number;
  delta: number;
  leaderModel: string;
  leaderPr: number;
  checkpoints: number;
  lastWk: number;
  full: boolean;
}
function RetrainPanel({ retrain, curDate, trainCount, pastCrossover }: { retrain: RetrainState; curDate: string; trainCount: number; pastCrossover: boolean }) {
  const leaderColor = MODEL_COLOR[retrain.leaderModel] ?? C.inkSoft;
  const dash = "—";
  return (
    <aside
      className="flex flex-col gap-2.5 rounded-lg p-3.5"
      style={{ background: C.card, border: `1px solid ${C.lineSoft}`, alignSelf: "start" }}
    >
      {/* 헤더 */}
      <div className="flex items-center gap-1.5">
        <span
          className="inline-block h-2 w-2 rounded-full"
          style={{ background: retrain.full ? C.forest : C.indigo }}
        />
        <h3 className="text-[11px] font-semibold uppercase tracking-wide" style={{ color: C.ink }}>
          재학습 현황
        </h3>
      </div>

      {/* 필수 정직 라벨 */}
      <div
        className="rounded-md px-2 py-1.5 text-[9px] leading-snug"
        style={{ background: C.paper2, color: C.amber, border: `1px dashed ${C.ochre}` }}
      >
        <b>데모용 사전 계산</b> · 실시간 재학습 아님
        <br />
        운영 시 월 1회 재학습 (Phase 2)
      </div>

      {/* 채택 모델(LightGBM, 최종 동결) PR-AUC */}
      <div>
        <div className="text-[9px] uppercase tracking-wide" style={{ color: C.muted }}>
          채택 모델 PR-AUC · LightGBM
        </div>
        <div className="font-mono text-2xl font-semibold tabular-nums leading-none" style={{ color: C.indigo }}>
          {retrain.started ? retrain.lgbmPr.toFixed(3) : dash}
        </div>
        {retrain.started && retrain.delta > 0 && (
          <div className="mt-0.5 text-[9.5px] font-mono" style={{ color: C.forest }}>
            ▲ +{retrain.delta.toFixed(3)} vs Dummy 0.387
          </div>
        )}
      </div>

      {/* 현재 선두 모델 (5개 중 argmax — 정직한 경쟁) */}
      <PanelRow label="현재 선두 (5개 중)">
        <span
          className="rounded px-1.5 py-0.5 text-[11px] font-semibold"
          style={{ background: retrain.started ? `${leaderColor}1A` : "transparent", color: retrain.started ? leaderColor : C.muted }}
        >
          {retrain.started ? `${MODEL_SHORT[retrain.leaderModel] ?? retrain.leaderModel} ${retrain.leaderPr.toFixed(3)}` : dash}
        </span>
      </PanelRow>

      {/* 학습 누적 예약 (좌측 스트림과 동일 기준 = 25k 시각화 샘플) */}
      <PanelRow label="학습 누적 예약">
        <span className="font-mono text-sm font-semibold tabular-nums" style={{ color: C.ink }}>
          {trainCount.toLocaleString("en-US")}
          <span className="ml-0.5 text-[10px] font-normal" style={{ color: C.muted }}>건</span>
        </span>
      </PanelRow>

      {/* 재학습 체크포인트 */}
      <PanelRow label="재학습 체크포인트">
        <span className="font-mono text-sm font-semibold tabular-nums" style={{ color: C.ink }}>
          {retrain.checkpoints}
          <span className="ml-0.5 text-[10px] font-normal" style={{ color: C.muted }}>회</span>
        </span>
      </PanelRow>

      {/* 컷오프 / 일정 (가상) */}
      <div className="mt-1 border-t pt-2 text-[9px] leading-relaxed" style={{ borderColor: C.lineSoft, color: C.muted }}>
        <div>
          데이터 컷오프{" "}
          <span className="font-mono" style={{ color: C.inkSoft }}>
            {retrain.started ? `wk ${retrain.lastWk}${curDate ? ` · ${curDate}` : ""}` : dash}
          </span>
        </div>
        <div className="mt-0.5" style={{ color: pastCrossover ? C.amber : C.muted }}>
          {retrain.full
            ? "전체 학습데이터 소진 · 모델 동결(freeze)"
            : "데이터 유입 → 주기적 재학습 재생 중"}
        </div>
      </div>
    </aside>
  );
}

function PanelRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-[10px]" style={{ color: C.muted }}>{label}</span>
      {children}
    </div>
  );
}
