"use client";

import { useEffect, useState } from "react";
import { getDashboardSummary, listBookings } from "@/lib/api";
import type { DashboardSummary, BookingListItem } from "@/types/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatRiskScore } from "@/types/api";
import { AlertTriangle, Zap, Hotel, Activity } from "lucide-react";
import Link from "next/link";
import { leadDays, daysUntilArrival, DEMO_AS_OF_LABEL } from "@/lib/demo";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  PieChart,
  Pie,
} from "recharts";

// ── 뷰 모드 타입 ──
type ViewMode = "overview" | "priority" | "list";

// 리드타임(예약→도착)·도착 카운트다운은 @/lib/demo (as-of 기준, 2017 스냅샷 호환)

// ── 위험도 색상 ──
function getRiskColor(score: number): string {
  if (score >= 0.7) return "var(--risk-high)";
  if (score >= 0.4) return "var(--risk-medium)";
  return "var(--risk-low)";
}

// ── Risk badge helper — inline bar 통합 ──
function RiskBadge({ score }: { score: number }) {
  const bg = getRiskColor(score);
  const label = score >= 0.7 ? "고" : score >= 0.4 ? "중" : "저";
  return (
    <div className="flex items-center gap-2">
      <span
        className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium text-white tabular-nums"
        style={{ backgroundColor: bg }}
      >
        {(score * 100).toFixed(1)}%
      </span>
      <div className="w-12 h-1 rounded-full bg-white/10 overflow-hidden">
        <div
          className="h-full rounded-full"
          style={{ width: `${score * 100}%`, backgroundColor: bg }}
        />
      </div>
      <span className="text-[10px] text-white/40 w-6">{label}</span>
    </div>
  );
}

// ── Scatter Tooltip ──
interface ScatterPayloadEntry {
  payload: {
    bookingId: string;
    hotel: string;
    country: string;
    riskScore: number;
    leadTime: number;
    raw: BookingListItem;
  };
}

interface ScatterTooltipProps {
  active?: boolean;
  payload?: ScatterPayloadEntry[];
}

function ScatterTooltip({ active, payload }: ScatterTooltipProps) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="rounded-lg border border-white/10 bg-[var(--bg-card)] p-3 text-xs shadow-xl">
      <p className="font-mono text-white/80">{d.bookingId}</p>
      <p className="text-white/50">
        {d.hotel} · {d.country}
      </p>
      <p className="mt-1" style={{ color: getRiskColor(d.riskScore) }}>
        위험도 {(d.riskScore * 100).toFixed(1)}%
      </p>
      <p className="text-white/40">리드타임 {d.leadTime}일</p>
    </div>
  );
}

// ── 예약 테이블 컴포넌트 ──
function BookingsTable({
  bookings,
  selectedBooking,
  onSelect,
  limit,
}: {
  bookings: BookingListItem[];
  selectedBooking: BookingListItem | null;
  onSelect: (b: BookingListItem | null) => void;
  limit?: number;
}) {
  const rows = limit ? bookings.slice(0, limit) : bookings;
  return (
    <Table>
      <TableHeader>
        <TableRow className="border-white/10 hover:bg-transparent">
          <TableHead className="text-white/50">예약 ID</TableHead>
          <TableHead className="text-white/50">호텔</TableHead>
          <TableHead className="text-white/50">국가</TableHead>
          <TableHead className="text-white/50">도착일</TableHead>
          <TableHead className="text-white/50">위험도</TableHead>
          <TableHead className="w-8" />
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.length === 0 ? (
          <TableRow className="border-white/10">
            <TableCell
              colSpan={6}
              className="text-center text-white/30 py-8"
            >
              데이터 로딩 중...
            </TableCell>
          </TableRow>
        ) : (
          rows.map((b) => (
            <TableRow
              key={b.booking_id}
              onClick={() =>
                onSelect(
                  selectedBooking?.booking_id === b.booking_id ? null : b
                )
              }
              className={[
                "border-white/10 cursor-pointer group transition-colors",
                selectedBooking?.booking_id === b.booking_id
                  ? "bg-white/10"
                  : "hover:bg-white/[0.04]",
                b.risk_score >= 0.7
                  ? "border-l-2 border-l-[var(--risk-high)]"
                  : b.risk_score >= 0.4
                  ? "border-l-2 border-l-[var(--risk-medium)]"
                  : "border-l-2 border-l-[var(--risk-low)]",
              ]
                .filter(Boolean)
                .join(" ")}
            >
              <TableCell className="font-mono text-xs text-white/80">
                {b.booking_id}
              </TableCell>
              <TableCell className="text-white/70">{b.hotel}</TableCell>
              <TableCell className="text-white/70">{b.country}</TableCell>
              <TableCell className="text-white/70">
                <div className="flex flex-col">
                  <span className="text-sm">
                    {new Date(b.arrival_date).toLocaleDateString("en", {
                      month: "short",
                      day: "numeric",
                    })}
                  </span>
                  <span className="text-[10px] text-white/30">
                    {daysUntilArrival(b.arrival_date)}d
                  </span>
                </div>
              </TableCell>
              <TableCell>
                <RiskBadge score={b.risk_score} />
              </TableCell>
              <TableCell className="text-right pr-4 w-8">
                <span className="text-white/20 group-hover:text-white/60 transition-colors text-xs">
                  →
                </span>
              </TableCell>
            </TableRow>
          ))
        )}
      </TableBody>
    </Table>
  );
}

export default function OverviewPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [bookings, setBookings] = useState<BookingListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selectedBooking, setSelectedBooking] =
    useState<BookingListItem | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("overview");

  useEffect(() => {
    async function fetchAll() {
      try {
        const [s, r] = await Promise.all([
          getDashboardSummary(),
          listBookings(),
        ]);
        setSummary(s);
        // 전체 장부를 위험도 내림차순으로 보관 (분포·산점도는 전체 기준, 표는 limit으로 상위만).
        const sorted = [...r.bookings].sort(
          (a, b) => b.risk_score - a.risk_score
        );
        setBookings(sorted);
        setError(null);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Unknown error");
      }
    }

    fetchAll();
    const timer = setInterval(fetchAll, 5000);
    return () => clearInterval(timer);
  }, []);

  const CURRENT_THRESHOLD = 0.65;

  // 산점도용 데이터 변환
  const scatterData = bookings.map((b) => ({
    bookingId: b.booking_id,
    hotel: b.hotel,
    country: b.country,
    riskScore: b.risk_score,
    leadTime: leadDays(b),
    raw: b,
  }));

  return (
    <div className="p-6 space-y-6 text-white">
      {/* 헤더 */}
      <div>
        <h1 className="text-xl font-semibold">현황</h1>
        {summary && (
          <p className="text-xs text-white/40 mt-0.5">
            데이터 갱신:{" "}
            {new Date(summary.last_updated).toLocaleTimeString()}
          </p>
        )}
      </div>

      {/* 신선도 · 모델 경계 — 정리=실시간 / 채점=정적 / 재학습=배치 (신뢰의 핵심 경계) */}
      <div className="rounded-xl border border-white/10 bg-[var(--bg-card)] px-4 py-3">
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
          <span className="text-[10px] uppercase tracking-wider text-white/40 shrink-0">신선도 · 모델 경계</span>
          {[
            { label: "정리(라우팅·피처화)", value: "실시간", color: "var(--risk-low)" },
            { label: "모델 채점", value: "정적 · LightGBM 0.820", color: "var(--flexi-color)" },
            { label: "재학습", value: "월 1회 배치 · 현재 freeze", color: "rgba(255,255,255,0.45)" },
          ].map((b) => (
            <span key={b.label} className="flex items-center gap-1.5 text-xs">
              <span className="h-1.5 w-1.5 rounded-full" style={{ background: b.color }} />
              <span className="text-white/40">{b.label}</span>
              <span className="font-medium" style={{ color: b.color }}>{b.value}</span>
            </span>
          ))}
          <span className="ml-auto text-[10px] text-white/30">
            기준일(as-of) {DEMO_AS_OF_LABEL} · 데모 성장곡선 = 사전계산 재생
          </span>
        </div>
      </div>

      {error && (
        <div className="rounded-md px-4 py-2 text-sm" style={{ backgroundColor: "color-mix(in srgb, var(--risk-high) 15%, transparent)", border: "1px solid color-mix(in srgb, var(--risk-high) 40%, transparent)", color: "var(--risk-high)" }}>
          API 연결 오류: {error} — 목업 서버가 실행 중인지 확인하세요.
        </div>
      )}

      {/* KPI Cards — 항상 표시 */}
      <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        {/* KPI 1 — 전체 예약 */}
        <Card className="bg-[var(--bg-card)] border-white/10 text-white">
          <CardHeader>
            <CardTitle className="flex items-center gap-1.5 text-xs text-white/50 font-normal">
              <Hotel size={12} style={{ color: "var(--risk-low)" }} />
              전체 예약
            </CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-3xl font-bold" style={{ color: "var(--risk-low)" }}>
              {summary?.total_bookings ?? "—"}
            </span>
            <p className="text-[10px] text-white/30 mt-1">캐글 테스트셋 · as-of 2017-06-01</p>
          </CardContent>
        </Card>

        {/* KPI 2 — 고위험 예약 */}
        <Card
          className="bg-[var(--bg-card)] text-white"
          style={
            summary && summary.high_risk_count > 0
              ? {
                  border: "1px solid color-mix(in srgb, var(--risk-high) 40%, transparent)",
                  boxShadow: "0 0 0 1px color-mix(in srgb, var(--risk-high) 20%, transparent)",
                }
              : { border: "1px solid rgba(255,255,255,0.1)" }
          }
        >
          <CardHeader>
            <CardTitle className="flex items-center gap-1.5 text-xs text-white/50 font-normal">
              <AlertTriangle size={12} style={{ color: "var(--risk-high)" }} />
              고위험 예약
            </CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-3xl font-bold" style={{ color: "var(--risk-high)" }}>
              {summary?.high_risk_count ?? "—"}
            </span>
            {summary && (
              <p className="text-xs text-white/40 mt-1">
                임계값 {(summary.current_threshold * 100).toFixed(0)}% 초과 — 즉시 확인 필요
              </p>
            )}
          </CardContent>
        </Card>

        {/* KPI 3 — Flexi 라우팅 */}
        <Card className="bg-[var(--bg-card)] border-white/10 text-white">
          <CardHeader>
            <CardTitle className="flex items-center gap-1.5 text-xs text-white/50 font-normal">
              <Zap size={12} style={{ color: "var(--flexi-color)" }} />
              Flexi 라우팅
            </CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-3xl font-bold" style={{ color: "var(--flexi-color)" }}>
              {summary?.flexi_routed_count ?? "—"}
            </span>
          </CardContent>
        </Card>

        {/* KPI 4 — 평균 위험도 */}
        <Card className="bg-[var(--bg-card)] border-white/10 text-white">
          <CardHeader>
            <CardTitle className="flex items-center gap-1.5 text-xs text-white/50 font-normal">
              <Activity size={12} className="text-white/70" />
              평균 위험도
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <span className="text-3xl font-bold">
              {summary ? formatRiskScore(summary.avg_risk_score) : "—"}
            </span>
            {summary && (
              <div className="mt-2">
                <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-700"
                    style={{
                      width: `${(summary?.avg_risk_score ?? 0) * 100}%`,
                      backgroundColor: (summary?.avg_risk_score ?? 0) >= 0.65
                        ? "var(--risk-high)"
                        : (summary?.avg_risk_score ?? 0) >= 0.4
                        ? "var(--risk-medium)"
                        : "var(--risk-low)"
                    }}
                  />
                </div>
                <div className="flex justify-between text-[9px] text-white/20 mt-0.5">
                  <span>0%</span>
                  <span className="text-yellow-400/50">임계값 65%</span>
                  <span>100%</span>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* 뷰 탭 */}
      <div className="flex items-center gap-1">
        {(
          [
            { key: "overview", label: "현황" },
            { key: "priority", label: "우선순위" },
            { key: "list", label: "전체" },
          ] as { key: ViewMode; label: string }[]
        ).map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setViewMode(key)}
            className={[
              "px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
              viewMode === key
                ? "bg-white/10 text-white"
                : "text-white/40 hover:text-white/70 hover:bg-white/5",
            ].join(" ")}
          >
            {label}
          </button>
        ))}
      </div>

      {/* viewMode별 콘텐츠 */}

      {/* ── Overview 탭 ── */}
      {viewMode === "overview" && (
        <div className="space-y-4">
          {/* Risk Overview Card — Overview 탭 기본 차트 */}
          <div className="rounded-xl border border-white/10 bg-[var(--bg-card)] p-6">
            <div className="mb-5">
              <h2 className="text-sm font-semibold text-white">위험 분포 현황</h2>
              <p className="text-xs text-white/40 mt-0.5">
                임계값 {Math.round(CURRENT_THRESHOLD * 100)}% 기준 — Flexi 풀 대상 {bookings.filter(b => b.risk_score >= CURRENT_THRESHOLD).length}건
              </p>
            </div>

            <div className="flex gap-8 items-center">
              {/* 도넛 차트 */}
              <div className="relative shrink-0">
                <ResponsiveContainer width={160} height={160}>
                  <PieChart>
                    <Pie
                      data={[
                        { name: "고위험", value: bookings.filter(b => b.risk_score >= 0.7).length, color: "var(--risk-high)" },
                        { name: "중위험", value: bookings.filter(b => b.risk_score >= 0.4 && b.risk_score < 0.7).length, color: "var(--risk-medium)" },
                        { name: "저위험", value: bookings.filter(b => b.risk_score < 0.4).length, color: "var(--risk-low)" },
                      ]}
                      cx={75}
                      cy={75}
                      innerRadius={48}
                      outerRadius={70}
                      paddingAngle={3}
                      dataKey="value"
                      strokeWidth={0}
                    >
                      {[
                        "var(--risk-high)",
                        "var(--risk-medium)",
                        "var(--risk-low)",
                      ].map((color, i) => (
                        <Cell key={i} fill={color} opacity={0.85} />
                      ))}
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
                {/* 중앙 숫자 — 고위험 강조 */}
                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                  <span className="text-2xl font-bold" style={{ color: "var(--risk-high)" }}>
                    {bookings.filter(b => b.risk_score >= 0.7).length}
                  </span>
                  <span className="text-[10px] text-white/40">고위험</span>
                  <span className="text-[10px] text-white/20">/ {bookings.length}건</span>
                </div>
              </div>

              {/* 범례 + 수치 */}
              <div className="space-y-3 flex-1">
                {[
                  { label: "고위험", min: 0.7, max: 1, color: "var(--risk-high)", desc: "즉시 Flexi 검토" },
                  { label: "중위험", min: 0.4, max: 0.7, color: "var(--risk-medium)", desc: "모니터링" },
                  { label: "저위험", min: 0, max: 0.4, color: "var(--risk-low)", desc: "정상" },
                ].map(({ label, min, max, color, desc }) => {
                  const count = bookings.filter(b => b.risk_score >= min && b.risk_score < max).length
                  const pct = bookings.length > 0 ? (count / bookings.length) * 100 : 0
                  return (
                    <div key={label} className="flex items-center gap-3">
                      <div className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: color }} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between mb-0.5">
                          <span className="text-xs text-white/70">{label}</span>
                          <span className="text-xs font-mono tabular-nums text-white/80">{count}건</span>
                        </div>
                        <div className="h-1 rounded-full bg-white/10 overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all duration-500"
                            style={{ width: `${pct}%`, backgroundColor: color, opacity: 0.7 }}
                          />
                        </div>
                      </div>
                      <span className="text-[10px] text-white/30 w-20 text-right shrink-0">{desc}</span>
                    </div>
                  )
                })}
              </div>

              {/* 구분선 */}
              <div className="w-px h-24 bg-white/10 shrink-0" />

              {/* 즉시 처리 목록 */}
              <div className="flex-1 min-w-0">
                <p className="text-xs text-white/40 mb-3">즉시 처리 필요</p>
                <div className="space-y-2">
                  {bookings
                    .filter(b => b.risk_score >= CURRENT_THRESHOLD)
                    .slice(0, 3)
                    .map(b => (
                      <div
                        key={b.booking_id}
                        className="flex items-center gap-3 group cursor-pointer"
                        onClick={() => setSelectedBooking(
                          selectedBooking?.booking_id === b.booking_id ? null : b
                        )}
                      >
                        <div
                          className="w-1 h-8 rounded-full shrink-0"
                          style={{ backgroundColor: b.risk_score >= 0.7 ? "var(--risk-high)" : "var(--risk-medium)" }}
                        />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-mono text-white/80">{b.booking_id}</span>
                            <span className="text-[10px] text-white/40">{b.country}</span>
                          </div>
                          <div className="flex items-center gap-1.5 mt-0.5">
                            <span
                              className="text-[10px] font-bold tabular-nums"
                              style={{ color: b.risk_score >= 0.7 ? "var(--risk-high)" : "var(--risk-medium)" }}
                            >
                              {Math.round(b.risk_score * 100)}%
                            </span>
                            {b.flexi_recommended && (
                              <span className="text-[10px] opacity-70" style={{ color: "var(--flexi-color)" }}>⚡ Flexi</span>
                            )}
                          </div>
                        </div>
                        <span className="text-white/20 group-hover:text-white/60 transition-colors text-xs">→</span>
                      </div>
                    ))}
                  {bookings.filter(b => b.risk_score >= CURRENT_THRESHOLD).length > 3 && (
                    <p className="text-[10px] text-white/30 pt-1">
                      + {bookings.filter(b => b.risk_score >= CURRENT_THRESHOLD).length - 3}건 더
                    </p>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* 예약 테이블 — 상위 5건 */}
          <Card className="bg-[var(--bg-card)] border-white/10 text-white">
            <CardHeader>
              <CardTitle className="text-sm">
                최근 예약 (위험도 상위 5건)
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <BookingsTable
                bookings={bookings}
                selectedBooking={selectedBooking}
                onSelect={setSelectedBooking}
                limit={5}
              />
              <div className="px-4 py-3 border-t border-white/10 text-right">
                <a
                  href="/dashboard/reservations"
                  className="text-xs text-white/30 hover:text-white/60 transition-colors"
                >
                  전체 {bookings.length}건 보기 →
                </a>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* ── Priority 탭 ── */}
      {viewMode === "priority" && (
        <div className="flex gap-4">
          {/* 산점도 + 테이블 */}
          <div className="flex-1 min-w-0 space-y-4">
            {/* 산점도 섹션 */}
            <div className="rounded-xl border border-white/10 bg-[var(--bg-card)] p-6">
              <div className="mb-4">
                <h2 className="text-sm font-semibold text-white">
                  리드타임 × 취소 위험도
                </h2>
                <p className="text-xs text-white/40 mt-0.5">
                  각 점 = 예약 1건. 클릭하면 상세 정보.
                </p>
              </div>
              <ResponsiveContainer width="100%" height={220}>
                <ScatterChart
                  margin={{ top: 10, right: 20, bottom: 20, left: 0 }}
                >
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="rgba(255,255,255,0.05)"
                  />
                  <XAxis
                    dataKey="leadTime"
                    type="number"
                    name="리드타임"
                    unit="일"
                    tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 11 }}
                    axisLine={{ stroke: "rgba(255,255,255,0.1)" }}
                    tickLine={false}
                    label={{
                      value: "리드타임 (일)",
                      position: "insideBottom",
                      offset: -10,
                      fill: "rgba(255,255,255,0.3)",
                      fontSize: 11,
                    }}
                  />
                  <YAxis
                    dataKey="riskScore"
                    type="number"
                    name="위험도"
                    domain={[0, 1]}
                    tickFormatter={(v: number) =>
                      `${(v * 100).toFixed(0)}%`
                    }
                    tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 11 }}
                    axisLine={{ stroke: "rgba(255,255,255,0.1)" }}
                    tickLine={false}
                    width={45}
                  />
                  <Tooltip
                    cursor={{
                      strokeDasharray: "3 3",
                      stroke: "rgba(255,255,255,0.2)",
                    }}
                    content={<ScatterTooltip />}
                  />
                  <Scatter
                    data={scatterData}
                    onClick={(data: unknown) => {
                      const d = data as { raw: BookingListItem };
                      if (d?.raw) setSelectedBooking(d.raw);
                    }}
                  >
                    {bookings.map((b) => (
                      <Cell
                        key={b.booking_id}
                        fill={getRiskColor(b.risk_score)}
                        opacity={
                          selectedBooking?.booking_id === b.booking_id
                            ? 1
                            : 0.75
                        }
                        stroke={
                          selectedBooking?.booking_id === b.booking_id
                            ? "white"
                            : "transparent"
                        }
                        strokeWidth={2}
                        r={6}
                      />
                    ))}
                  </Scatter>
                </ScatterChart>
              </ResponsiveContainer>

              {/* 범례 */}
              <div className="flex gap-4 mt-2 justify-end">
                <span className="flex items-center gap-1.5 text-[10px] text-white/40">
                  <span className="w-2 h-2 rounded-full bg-[var(--risk-high)]" />
                  고위험 (≥70%)
                </span>
                <span className="flex items-center gap-1.5 text-[10px] text-white/40">
                  <span className="w-2 h-2 rounded-full bg-[var(--risk-medium)]" />
                  중위험 (40-70%)
                </span>
                <span className="flex items-center gap-1.5 text-[10px] text-white/40">
                  <span className="w-2 h-2 rounded-full bg-[var(--risk-low)]" />
                  저위험 (&lt;40%)
                </span>
                <span className="flex items-center gap-1.5 text-[10px] opacity-60" style={{ color: "var(--flexi-color)" }}>
                  <span className="text-[10px]">---</span> Flexi 임계값 (65%)
                </span>
              </div>
            </div>

            {/* 전체 10건 테이블 */}
            <Card className="bg-[var(--bg-card)] border-white/10 text-white">
              <CardHeader>
                <CardTitle className="text-sm">
                  예약 목록 (위험도순)
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <BookingsTable
                  bookings={bookings}
                  selectedBooking={selectedBooking}
                  onSelect={setSelectedBooking}
                />
              </CardContent>
            </Card>
          </div>

          {/* 상세 패널 — selectedBooking 있을 때만 표시 */}
          {selectedBooking && (
            <div className="w-72 shrink-0 rounded-xl border border-white/10 bg-[var(--bg-card)] p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-white">예약 상세</h3>
                <div className="flex items-center gap-2">
                  <Link
                    href={`/dashboard/reservations/${selectedBooking.booking_id}`}
                    className="text-[11px] text-white/30 hover:text-white/70 transition-colors"
                  >
                    전체 보기 →
                  </Link>
                  <button
                    onClick={() => setSelectedBooking(null)}
                    className="text-white/30 hover:text-white/70 transition-colors text-lg leading-none"
                  >
                    ×
                  </button>
                </div>
              </div>

              {/* 위험도 게이지 */}
              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <span className="text-xs text-white/40">취소 위험도</span>
                  <span
                    className="text-sm font-bold tabular-nums"
                    style={{ color: getRiskColor(selectedBooking.risk_score) }}
                  >
                    {(selectedBooking.risk_score * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="h-2 rounded-full bg-white/10 overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${selectedBooking.risk_score * 100}%`,
                      backgroundColor: getRiskColor(selectedBooking.risk_score),
                    }}
                  />
                </div>
              </div>

              {/* 예약 정보 */}
              <div className="space-y-2 text-xs">
                {(
                  [
                    [
                      "예약 ID",
                      <span key="id" className="font-mono text-white/80">
                        {selectedBooking.booking_id}
                      </span>,
                    ],
                    ["호텔", selectedBooking.hotel],
                    ["국가", selectedBooking.country],
                    [
                      "도착일",
                      new Date(
                        selectedBooking.arrival_date
                      ).toLocaleDateString("ko", {
                        month: "short",
                        day: "numeric",
                      }),
                    ],
                    [
                      "리드타임",
                      `${leadDays(selectedBooking)}일`,
                    ],
                    ["숙박", `${selectedBooking.nights}박`],
                    ["인원", `${selectedBooking.adults}명`],
                  ] as [string, React.ReactNode][]
                ).map(([label, value]) => (
                  <div key={String(label)} className="flex justify-between">
                    <span className="text-white/40">{label}</span>
                    <span className="text-white/80">{value}</span>
                  </div>
                ))}
              </div>

              {/* Flexi 권장 여부 */}
              {selectedBooking.flexi_recommended && (
                <div
                  className="rounded-lg p-3"
                  style={{
                    backgroundColor: "color-mix(in srgb, var(--flexi-color) 10%, transparent)",
                    border: "1px solid color-mix(in srgb, var(--flexi-color) 20%, transparent)",
                  }}
                >
                  <p className="text-xs font-semibold" style={{ color: "var(--flexi-color)" }}>
                    Flexi 라우팅 권장
                  </p>
                  <p className="text-xs mt-1 opacity-60" style={{ color: "var(--flexi-color)" }}>
                    할인율{" "}
                    {selectedBooking.discount_rate
                      ? `${(selectedBooking.discount_rate * 100).toFixed(1)}%`
                      : "—"}{" "}
                    적용
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── List 탭 ── */}
      {viewMode === "list" && (
        <div>
          <Card className="bg-[var(--bg-card)] border-white/10 text-white">
            <CardHeader>
              <CardTitle className="text-sm">
                전체 예약 (위험도순)
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <BookingsTable
                bookings={bookings}
                selectedBooking={selectedBooking}
                onSelect={setSelectedBooking}
              />
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
