"use client";

/**
 * Domain Inbox — "하나의 수집 인프라 → 여러 비즈니스 도메인" 라우팅 콘솔
 * ------------------------------------------------------------------
 * 덱 S12(EXTENSIBILITY)를 앱에서 실물화: 동일하게 수집되는 예약 스트림이
 * 4개 비즈니스 도메인으로 규칙 라우팅된다.
 *
 * 정직 프레이밍(덱 S12와 동일):
 *  - 도메인 1(오버부킹)만 실제 학습 모델(LightGBM) — risk_score가 실모델 출력.
 *  - 도메인 2~4는 "동일 수집 데이터에 규칙 기반 라우팅"을 적용한 확장성 데모(모델 미학습).
 *  - 규칙은 화면에 그대로 노출(블랙박스 아님). 새 수치 날조 없음 — 라우팅 신호는
 *    백엔드 예약 목록의 실제 필드(risk_score / nights / adults / arrival / lead)에서만 나온다.
 *
 * 데이터: lib/api.listBookings() (백엔드 8001 · 나머지 대시보드 탭과 동일 의존).
 */

import { useCallback, useEffect, useState } from "react";
import { listBookings, getDashboardSummary } from "@/lib/api";
import type { BookingListItem, DashboardSummary } from "@/types/api";
import { getCountryFlag } from "@/types/api";
import { leadDays } from "@/lib/demo";

function arrivalMonth(arrival: string): number {
  return new Date(arrival).getMonth() + 1; // 1~12
}

type DomainStatus = "live" | "rule" | "planned";

interface DomainDef {
  n: number;
  name: string;
  inputs: string;   // 입력 신호 — 이 기준이 소비하는 필드
  criteria: string; // 판단 기준 — 라우팅 규칙/모델 결정 로직
  output: string;   // 권장 출력 — 이 기준이 내는 권고
  status: DomainStatus;
  color: string;    // 카드 액센트
  route: (b: BookingListItem) => { hit: boolean; signal: string };
}

// ── 4 판단 기준(criteria) 정의 (덱 S12 공식 세트) ─────────────────────
// criteria 텍스트 = 이 보드(백엔드 예약)에서 실제로 쓰는 라우팅 규칙과 일치(정직).
const DOMAINS: DomainDef[] = [
  {
    n: 1,
    name: "오버부킹",
    inputs: "취소위험 · lead_time",
    criteria: "위험 ≥ 50% · 뉴스벤더 임계(이득=손해 지점)",
    output: "오버부킹 세그먼트 8~30%",
    status: "live",
    color: "var(--risk-high)", // rose
    route: (b) => ({ hit: b.risk_score >= 0.5, signal: `위험 ${Math.round(b.risk_score * 100)}%` }),
  },
  {
    n: 2,
    name: "부가 매출",
    inputs: "숙박일수 · 인원",
    criteria: "3박 이상 또는 3인 이상",
    output: "객실 업그레이드 · 식음료 추가판매",
    status: "rule",
    color: "var(--flexi-color)", // amber
    route: (b) => ({
      hit: b.nights >= 3 || b.adults >= 3,
      signal: `${b.nights}박 · ${b.adults}인`,
    }),
  },
  {
    n: 3,
    name: "동적 가격",
    inputs: "lead_time · 수요",
    criteria: "리드타임 90일 이상",
    output: "가격 탄력 조정 권고",
    status: "planned",
    color: "#60A5FA", // blue-400
    route: (b) => {
      const d = leadDays(b);
      return { hit: d >= 90, signal: `리드 ${d}일` };
    },
  },
  {
    n: 4,
    name: "수요 · 인력",
    inputs: "도착월 · 인원",
    criteria: "성수기(6~8월) 도착 또는 3인+ 단체",
    output: "인력 배치 · 수요 예측",
    status: "planned",
    color: "#A78BFA", // violet-400
    route: (b) => {
      const m = arrivalMonth(b.arrival_date);
      const peak = m >= 6 && m <= 8;
      return { hit: peak || b.adults >= 3, signal: peak ? "성수기 도착" : `${b.adults}인 단체` };
    },
  },
];

// 색상별 반투명 배경/테두리 (Overview가 쓰는 color-mix 패턴 — Tailwind /opacity 회피)
function tint(color: string, pct: number): string {
  return `color-mix(in srgb, ${color} ${pct}%, transparent)`;
}
const STATUS_BADGE: Record<DomainStatus, { label: string; color: string }> = {
  live: { label: "실모델 · LightGBM", color: "var(--risk-low)" },
  rule: { label: "규칙 기반 라우팅", color: "var(--flexi-color)" },
  planned: { label: "확장 설계 (규칙 데모)", color: "rgba(255,255,255,0.55)" },
};

export default function DomainInbox() {
  const [bookings, setBookings] = useState<BookingListItem[]>([]);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchAll = useCallback(async () => {
    try {
      const [r, s] = await Promise.all([listBookings(), getDashboardSummary()]);
      setBookings(r.bookings);
      setSummary(s);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    }
  }, []);

  useEffect(() => {
    fetchAll();
    const t = setInterval(fetchAll, 5000);
    return () => clearInterval(t);
  }, [fetchAll]);

  // 도메인별 라우팅 결과
  const routed = DOMAINS.map((d) => {
    const items = bookings
      .map((b) => ({ b, ...d.route(b) }))
      .filter((x) => x.hit);
    return { domain: d, items };
  });

  const activeDomains = DOMAINS.filter((d) => d.status === "live").length;

  return (
    <div className="space-y-6 text-white">
      {/* 헤더 — 정제 레이어 철학 */}
      <div>
        <h1 className="text-xl font-semibold">도메인 인박스 <span className="text-xs font-normal text-white/40">· 판단 기준(criteria) 레이어</span></h1>
        <p className="text-xs text-white/40 mt-0.5">
          raw 데이터가 아니라 <span className="text-white/65">검증된 판단 기준(criteria)</span>으로 정리된 컨텍스트 — 어떤 AI/모델도 이 위에선 더 잘 판단합니다.
        </p>
      </div>

      {error && (
        <div
          className="rounded-md px-4 py-2 text-sm"
          style={{
            backgroundColor: "color-mix(in srgb, var(--risk-high) 15%, transparent)",
            border: "1px solid color-mix(in srgb, var(--risk-high) 40%, transparent)",
            color: "var(--risk-high)",
          }}
        >
          API 연결 오류: {error} — 백엔드(8001)가 실행 중인지 확인하세요.
        </div>
      )}

      {/* ── 수집 인프라 → 도메인 라우팅 (인프라 프레이밍) ── */}
      <div className="rounded-xl border border-white/10 bg-[var(--bg-card)] p-5">
        <div className="flex flex-wrap items-center gap-x-6 gap-y-4">
          {/* 좌: 수집 인프라 */}
          <div className="min-w-0">
            <div className="text-[10px] uppercase tracking-wider text-white/40">수집 인프라</div>
            <div className="mt-1 flex items-baseline gap-3">
              <span className="font-mono text-2xl font-bold tabular-nums">38</span>
              <span className="text-xs text-white/50">피처 스키마</span>
              <span className="text-white/20">·</span>
              <span className="font-mono text-2xl font-bold tabular-nums">119,390</span>
              <span className="text-xs text-white/50">학습 누적(전체)</span>
            </div>
            <div className="mt-1 text-[11px] text-white/40">
              실시간 수집 <span className="font-mono text-white/70">{summary?.total_bookings ?? "—"}</span>건
              (목업 PMS 유입)
            </div>
          </div>

          {/* 화살표 */}
          <div className="text-white/25 text-2xl">→</div>

          {/* 우: 도메인 라우팅 */}
          <div className="flex-1 min-w-0">
            <div className="text-[10px] uppercase tracking-wider text-white/40">도메인 라우팅</div>
            <div className="mt-2 flex flex-wrap gap-2">
              {DOMAINS.map((d) => (
                <span
                  key={d.n}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 px-2.5 py-1 text-xs"
                  style={{ background: "rgba(255,255,255,0.02)" }}
                >
                  <span className="h-2 w-2 rounded-full" style={{ background: d.color }} />
                  <span className="text-white/75">{d.n}. {d.name}</span>
                </span>
              ))}
            </div>
          </div>

          {/* 활성 카운트 */}
          <div className="text-right">
            <div className="text-[10px] uppercase tracking-wider text-white/40">활성 / 설계</div>
            <div className="font-mono text-2xl font-bold tabular-nums">
              {activeDomains}<span className="text-white/30 text-lg"> / {DOMAINS.length}</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── 도메인 칸반 (4열) ── */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {routed.map(({ domain: d, items }) => {
          const badge = STATUS_BADGE[d.status];
          return (
            <div
              key={d.n}
              className="flex flex-col rounded-xl border border-white/10 bg-[var(--bg-card)] overflow-hidden"
            >
              {/* criteria card 헤더 */}
              <div className="p-3.5 border-b border-white/10" style={{ borderTop: `2px solid ${d.color}` }}>
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="font-mono text-[11px] text-white/40">D{d.n}</span>
                    <h3 className="text-sm font-semibold truncate">{d.name}</h3>
                  </div>
                  <div className="text-right shrink-0">
                    <span className="font-mono text-xl font-bold tabular-nums leading-none" style={{ color: d.color }}>{items.length}</span>
                    <div className="text-[8.5px] text-white/30">실시간 라우팅</div>
                  </div>
                </div>
                {/* 성숙도 + AI-ready 배지 */}
                <div className="mt-2 flex flex-wrap gap-1">
                  <span className="rounded-md border px-1.5 py-0.5 text-[9px] font-medium"
                    style={{ background: tint(badge.color, 14), color: badge.color, borderColor: tint(badge.color, 32) }}>
                    {badge.label}
                  </span>
                  <span className="rounded-md border px-1.5 py-0.5 text-[9px] font-medium"
                    style={{ background: tint("#22D3EE", 12), color: "#22D3EE", borderColor: tint("#22D3EE", 28) }}>
                    AI-ready
                  </span>
                </div>
                {/* 판단 기준 3행: 입력 → 기준 → 권장 */}
                <dl className="mt-3 space-y-1">
                  <CriteriaRow k="입력" v={d.inputs} />
                  <CriteriaRow k="기준" v={d.criteria} />
                  <CriteriaRow k="권장" v={d.output} accent={d.color} />
                </dl>
              </div>

              {/* 라우팅된 예약 목록 */}
              <div className="flex-1 p-2 space-y-1.5 overflow-y-auto" style={{ maxHeight: 360 }}>
                {items.length === 0 ? (
                  <div className="py-8 text-center text-[11px] text-white/25">대상 예약 없음</div>
                ) : (
                  items.map(({ b, signal }) => (
                    <div
                      key={b.booking_id}
                      className="rounded-lg border border-white/[0.06] bg-white/[0.02] px-2.5 py-2"
                      style={{ borderLeft: `2px solid ${d.color}` }}
                    >
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs">{getCountryFlag(b.country)}</span>
                        <span className="font-mono text-[11px] text-white/70 truncate">{b.booking_id}</span>
                        <span className="ml-auto font-mono text-[10px] tabular-nums shrink-0" style={{ color: d.color }}>
                          {signal}
                        </span>
                      </div>
                      <div className="mt-0.5 flex items-center gap-1.5 text-[10px] text-white/35">
                        <span>{b.hotel.replace(" Hotel", "")}</span>
                        <span className="text-white/15">·</span>
                        <span>{b.country}</span>
                        {b.flexi_recommended && (
                          <span className="ml-auto" style={{ color: "var(--flexi-color)" }}>⚡</span>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* ── 정직성 각주 ── */}
      <div className="rounded-lg border border-white/10 bg-white/[0.015] px-4 py-3 text-[11px] leading-relaxed text-white/45">
        <span className="text-white/65 font-medium">정직성 ·</span>{" "}
        도메인 1(오버부킹)만 실제 학습 모델(LightGBM, PR-AUC 0.820)입니다. 도메인 2~4는{" "}
        <span className="text-white/65">동일 수집 데이터에 규칙 기반 라우팅</span>을 적용한 확장성 데모로,
        아직 모델을 학습하지 않았습니다(덱 S12에서 정직하게 &lsquo;비전&rsquo;으로 표기한 것과 동일).
        한 예약은 여러 도메인에 동시 라우팅될 수 있습니다 — 같은 데이터베이스 하나가 여러 도메인을 연다는 뜻입니다.
      </div>
    </div>
  );
}

// criteria card 한 행 (입력/기준/권장)
function CriteriaRow({ k, v, accent }: { k: string; v: string; accent?: string }) {
  return (
    <div className="flex gap-2 text-[10px] leading-snug">
      <dt className="w-7 shrink-0 text-white/30">{k}</dt>
      <dd className="flex-1 min-w-0" style={{ color: accent ?? "rgba(255,255,255,0.62)" }}>{v}</dd>
    </div>
  );
}
