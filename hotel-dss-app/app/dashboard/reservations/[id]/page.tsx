"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { getBooking, getBookingAnalysis } from "@/lib/api";
import type { BookingListItem, BookingAnalysis } from "@/types/api";
import { daysUntilArrival } from "@/lib/demo";

function getRiskColor(score: number): string {
  if (score >= 0.7) return "var(--risk-high)";
  if (score >= 0.4) return "var(--risk-medium)";
  return "var(--risk-low)";
}

export default function BookingDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  const [booking, setBooking] = useState<BookingListItem | null>(null);
  const [analysis, setAnalysis] = useState<BookingAnalysis | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getBooking(id),
      getBookingAnalysis(id).catch(() => null),
    ])
      .then(([b, a]) => {
        setBooking(b);
        setAnalysis(a);
      })
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return <div className="p-6 text-white/40 text-sm">로딩 중...</div>;
  }
  if (!booking) {
    return (
      <div className="p-6 text-white/40 text-sm">예약을 찾을 수 없습니다.</div>
    );
  }

  const leadTime = daysUntilArrival(booking.arrival_date);
  const riskColor = getRiskColor(booking.risk_score);

  return (
    <div className="p-6 max-w-4xl space-y-6 text-white">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link
            href="/dashboard/reservations"
            className="text-white/30 hover:text-white/70 transition-colors text-sm"
          >
            ← 목록
          </Link>
          <span className="text-white/20">/</span>
          <h1 className="text-base font-semibold text-white font-mono">
            {booking.booking_id}
          </h1>
          <span
            className="text-xs px-2 py-0.5 rounded-full font-medium text-white"
            style={{ backgroundColor: riskColor }}
          >
            {Math.round(booking.risk_score * 100)}%
          </span>
        </div>
        {/* 매니저 액션 버튼 */}
        <div className="flex gap-2">
          {booking.flexi_recommended && (
            <button className="px-4 py-1.5 rounded-lg bg-amber-500/20 border border-amber-500/30 text-amber-300 text-sm font-medium hover:bg-amber-500/30 transition-all">
              Flexi 확정
            </button>
          )}
          <button className="px-4 py-1.5 rounded-lg bg-white/5 border border-white/10 text-white/60 text-sm hover:bg-white/10 transition-all">
            Override
          </button>
        </div>
      </div>

      {/* 2컬럼 레이아웃 */}
      <div className="grid grid-cols-2 gap-6">
        {/* 왼쪽: 예약 상세 정보 */}
        <div className="rounded-xl border border-white/10 bg-[var(--bg-card)] p-5">
          <h2 className="text-xs font-semibold text-white/50 uppercase tracking-wider mb-4">
            예약 정보
          </h2>
          <dl className="space-y-2.5">
            {(
              [
                ["호텔", booking.hotel],
                ["국적", booking.country],
                [
                  "도착일",
                  `${new Date(booking.arrival_date).toLocaleDateString("en", {
                    month: "short",
                    day: "numeric",
                    year: "numeric",
                  })} (${leadTime > 0 ? `D-${leadTime}` : "오늘 이후"})`,
                ],
                ["숙박", `${booking.nights}박`],
                ["성인", `${booking.adults}명`],
                [
                  "위험도",
                  <span
                    key="risk"
                    style={{ color: riskColor }}
                    className="font-bold"
                  >
                    {Math.round(booking.risk_score * 100)}%
                  </span>,
                ],
                [
                  "Flexi 여부",
                  booking.flexi_recommended ? (
                    <span key="flexi" className="text-amber-400">
                      Flexi 권장
                    </span>
                  ) : (
                    <span key="std" className="text-emerald-400">
                      Standard
                    </span>
                  ),
                ],
                [
                  "할인율",
                  booking.discount_rate
                    ? `${Math.round(booking.discount_rate * 100)}%`
                    : "—",
                ],
                [
                  "등록일",
                  new Date(booking.created_at).toLocaleDateString("ko", {
                    month: "short",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  }),
                ],
              ] as [string, React.ReactNode][]
            ).map(([label, value]) => (
              <div
                key={String(label)}
                className="flex justify-between items-center py-1 border-b border-white/5 last:border-0"
              >
                <dt className="text-xs text-white/40">{label}</dt>
                <dd className="text-xs text-white/80 text-right">{value}</dd>
              </div>
            ))}
          </dl>
        </div>

        {/* 오른쪽: 위험도 분석 */}
        <div className="rounded-xl border border-white/10 bg-[var(--bg-card)] p-5">
          <h2 className="text-xs font-semibold text-white/50 uppercase tracking-wider mb-4">
            위험도 분석
          </h2>

          {/* 메인 게이지 */}
          <div className="mb-5">
            <div className="flex justify-between items-end mb-2">
              <span className="text-xs text-white/40">취소 위험도</span>
              <span
                className="text-2xl font-bold tabular-nums"
                style={{ color: riskColor }}
              >
                {Math.round(booking.risk_score * 100)}%
              </span>
            </div>
            <div className="h-2 rounded-full bg-white/10 overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-700"
                style={{
                  width: `${booking.risk_score * 100}%`,
                  backgroundColor: riskColor,
                }}
              />
            </div>
            <div className="flex justify-between text-[9px] text-white/20 mt-1">
              <span>저위험</span>
              <span className="text-amber-400/50">임계값 65%</span>
              <span>고위험</span>
            </div>
          </div>

          {/* SHAP 위험 요인 (analysis 있을 때만) */}
          {analysis && analysis.top_risk_factors.length > 0 && (
            <div>
              <p className="text-xs text-white/40 mb-3">
                위험 요인 (SHAP 기여도)
              </p>
              <div className="space-y-2">
                {analysis.top_risk_factors.map((f, i) => {
                  const isPositive = f.shap_value > 0;
                  const barWidth = Math.min(
                    (Math.abs(f.shap_value) / 5) * 100,
                    100
                  );
                  return (
                    <div key={i} className="flex items-center gap-2">
                      <span className="text-[10px] text-white/20 w-4 text-right shrink-0">
                        {i + 1}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="text-[11px] text-white/70 truncate">
                          {f.label}
                        </p>
                        <div className="mt-0.5 h-1 rounded-full bg-white/5 overflow-hidden">
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${barWidth}%`,
                              backgroundColor: isPositive
                                ? "var(--risk-high)"
                                : "var(--risk-low)",
                              opacity: 0.7,
                            }}
                          />
                        </div>
                      </div>
                      <span
                        className="text-[10px] font-mono tabular-nums w-12 text-right shrink-0"
                        style={{
                          color: isPositive
                            ? "var(--risk-high)"
                            : "var(--risk-low)",
                        }}
                      >
                        {f.shap_value > 0 ? "+" : ""}
                        {f.shap_value.toFixed(2)}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* analysis 없을 때 안내 */}
          {!analysis && (
            <p className="text-[11px] text-white/20 mt-2">
              SHAP 분석 데이터를 불러올 수 없습니다.
            </p>
          )}
        </div>
      </div>

      {/* Flexi 결정 근거 패널 */}
      {booking.flexi_recommended && (
        <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-5">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-sm font-semibold text-amber-300 flex items-center gap-2">
                <span>Flexi Rate 배정 권장</span>
              </h2>
              {analysis?.flexi_rationale && (
                <p className="text-xs text-amber-400/60 mt-2 leading-relaxed max-w-lg">
                  {analysis.flexi_rationale}
                </p>
              )}
            </div>
            {analysis &&
              (analysis.estimated_loss_if_cancel > 0 ||
                analysis.estimated_flexi_discount > 0) && (
                <div className="text-right shrink-0 ml-6">
                  <div className="text-xs text-white/40 mb-1">비용 비교</div>
                  <div className="space-y-1">
                    <div className="flex items-center gap-3 justify-end">
                      <span className="text-[10px] text-white/40">
                        취소 시 손실
                      </span>
                      <span className="text-sm font-mono text-red-400">
                        {analysis.estimated_loss_if_cancel.toFixed(0)}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 justify-end">
                      <span className="text-[10px] text-white/40">
                        Flexi 할인 비용
                      </span>
                      <span className="text-sm font-mono text-amber-400">
                        {analysis.estimated_flexi_discount.toFixed(0)}
                      </span>
                    </div>
                  </div>
                </div>
              )}
          </div>
        </div>
      )}
    </div>
  );
}
