"use client";

import { useEffect, useState } from "react";
import { getPMSReservations } from "@/lib/pms-api";
import type { PMSReservationRecord, PricingType } from "@/types/pms";
import { PERSONA_BY_ID } from "@/types/pms";
import Link from "next/link";

type FilterTab = "all" | "flexi" | "standard";

function Avatar({ initials, color, size = 32 }: { initials: string; color: string; size?: number }) {
  return (
    <div
      className="flex items-center justify-center rounded-full font-bold shrink-0"
      style={{
        width: size, height: size,
        backgroundColor: color + "33",
        border: `2px solid ${color}55`,
        fontSize: size * 0.33,
        color,
      }}
    >
      {initials}
    </div>
  );
}

function FlexiBadge({ type, discount }: { type: PricingType; discount: number | null }) {
  if (type === "Flexi Rate") {
    return (
      <span
        className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold whitespace-nowrap"
        style={{ backgroundColor: "#F59E0B22", color: "#F59E0B", border: "1px solid #F59E0B44" }}
      >
        ⚡ Flexi {discount ? `-${(discount * 100).toFixed(1)}%` : ""}
      </span>
    );
  }
  return (
    <span
      className="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold"
      style={{ backgroundColor: "#34D39922", color: "#34D399", border: "1px solid #34D39944" }}
    >
      Standard
    </span>
  );
}

export default function PMSReservationsPage() {
  const [reservations, setReservations] = useState<PMSReservationRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterTab>("all");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    async function fetch() {
      try {
        const r = await getPMSReservations();
        setReservations(r.reservations);
        setError(null);
      } catch (e) {
        setError(e instanceof Error ? e.message : "PMS 서버 연결 실패");
      }
    }
    fetch();
    const t = setInterval(fetch, 3000);
    return () => clearInterval(t);
  }, []);

  const filtered = reservations.filter((r) => {
    if (filter === "flexi") return r.pricing_type === "Flexi Rate";
    if (filter === "standard") return r.pricing_type === "Standard Rate";
    return true;
  });

  const flexi = reservations.filter(r => r.pricing_type === "Flexi Rate").length;
  const standard = reservations.filter(r => r.pricing_type === "Standard Rate").length;
  const selected = reservations.find(r => r.confirmation_number === selectedId) ?? null;

  const TABS: { key: FilterTab; label: string; count: number }[] = [
    { key: "all",      label: "All",      count: reservations.length },
    { key: "flexi",    label: "Flexi Rate",    count: flexi },
    { key: "standard", label: "Standard Rate", count: standard },
  ];

  return (
    <div className="p-6 text-white space-y-5">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Reservations</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            {reservations.length}건 · LLM 에이전트 예약 전체 내역
          </p>
        </div>
        <Link
          href="/pms"
          className="text-[11px] text-slate-600 hover:text-blue-400 transition-colors"
        >
          ← Dashboard
        </Link>
      </div>

      {error && (
        <div className="rounded-lg px-4 py-3 text-sm bg-red-500/10 border border-red-500/30 text-red-400">
          {error}
        </div>
      )}

      {/* 필터 탭 */}
      <div className="flex gap-1">
        {TABS.map(({ key, label, count }) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            className={[
              "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
              filter === key
                ? "bg-slate-700 text-white"
                : "text-slate-500 hover:text-slate-300 hover:bg-slate-800",
            ].join(" ")}
          >
            {label}
            <span className={[
              "rounded-full px-1.5 py-0 text-[10px] tabular-nums",
              filter === key ? "bg-slate-600 text-white" : "bg-slate-800 text-slate-600"
            ].join(" ")}>
              {count}
            </span>
          </button>
        ))}
      </div>

      {/* 메인 레이아웃 */}
      <div className="flex gap-4">
        {/* 테이블 */}
        <div className="flex-1 rounded-xl border border-slate-800 bg-slate-900 overflow-hidden">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-slate-800">
                {["확인번호", "게스트", "호텔", "도착일 ~ 체크아웃", "룸", "식사", "요금제", "금액", "DSS"].map(h => (
                  <th key={h} className="px-3 py-2.5 text-left text-slate-600 font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={9} className="px-4 py-12 text-center text-slate-700">
                    {reservations.length === 0
                      ? "시뮬레이션 실행 후 예약이 표시됩니다"
                      : "해당 필터에 맞는 예약이 없습니다"}
                  </td>
                </tr>
              ) : (
                filtered.map((r) => {
                  const persona = PERSONA_BY_ID[r.agent_id];
                  const isSelected = selectedId === r.confirmation_number;
                  return (
                    <tr
                      key={r.confirmation_number}
                      onClick={() => setSelectedId(isSelected ? null : r.confirmation_number)}
                      className={[
                        "border-b border-slate-800/50 cursor-pointer transition-colors",
                        isSelected ? "bg-slate-800" : "hover:bg-slate-800/40",
                      ].join(" ")}
                    >
                      <td className="px-3 py-3 font-mono text-slate-300">{r.confirmation_number}</td>
                      <td className="px-3 py-3">
                        <div className="flex items-center gap-2">
                          {persona && (
                            <Avatar initials={persona.avatar_initials} color={persona.avatar_color} size={28} />
                          )}
                          <div>
                            <p className="text-slate-200 font-medium">{r.persona_name}</p>
                            <p className="text-slate-600 text-[10px]">{r.persona_nationality} · {r.persona_type}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-3 py-3 text-slate-400 whitespace-nowrap">{r.hotel.replace(" Hotel", "")}</td>
                      <td className="px-3 py-3 text-slate-400 whitespace-nowrap">
                        {r.arrival_date} ~ {r.departure_date}
                        <span className="ml-1 text-slate-600">({r.nights}박)</span>
                      </td>
                      <td className="px-3 py-3 text-slate-500">{r.room_type_assigned}</td>
                      <td className="px-3 py-3 text-slate-500">{r.meal_plan}</td>
                      <td className="px-3 py-3">
                        <FlexiBadge type={r.pricing_type} discount={r.discount_applied} />
                      </td>
                      <td className="px-3 py-3 font-mono text-slate-300">€{r.total_amount.toFixed(0)}</td>
                      <td className="px-3 py-3">
                        {r.dss_risk_score !== null ? (
                          <div className="flex items-center gap-1.5">
                            <span
                              className="font-mono font-semibold text-[11px]"
                              style={{
                                color: r.dss_risk_score >= 0.7 ? "#FB7185"
                                     : r.dss_risk_score >= 0.4 ? "#FBBF24" : "#34D399"
                              }}
                            >
                              {(r.dss_risk_score * 100).toFixed(1)}%
                            </span>
                            {r.dss_booking_id && (
                              <Link
                                href={`/dashboard/reservations/${r.dss_booking_id}`}
                                onClick={e => e.stopPropagation()}
                                className="text-[10px] text-slate-700 hover:text-blue-400 transition-colors"
                              >
                                →
                              </Link>
                            )}
                          </div>
                        ) : (
                          <span className="text-slate-700">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* 상세 패널 */}
        {selected && (() => {
          const persona = PERSONA_BY_ID[selected.agent_id];
          return (
            <div className="w-64 shrink-0 rounded-xl border border-slate-800 bg-slate-900 p-4 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-200">예약 상세</h3>
                <button
                  onClick={() => setSelectedId(null)}
                  className="text-slate-600 hover:text-slate-300 transition-colors"
                >
                  ×
                </button>
              </div>

              {/* 페르소나 */}
              {persona && (
                <div className="flex items-center gap-3 p-3 rounded-lg" style={{ backgroundColor: persona.avatar_color + "11", border: `1px solid ${persona.avatar_color}22` }}>
                  <Avatar initials={persona.avatar_initials} color={persona.avatar_color} size={40} />
                  <div>
                    <p className="text-sm font-semibold" style={{ color: persona.avatar_color }}>
                      {persona.name} {persona.flag}
                    </p>
                    <p className="text-[11px] text-slate-500">{persona.persona_type}</p>
                    <p className="text-[10px] text-slate-700 mt-0.5 line-clamp-2">{persona.description}</p>
                  </div>
                </div>
              )}

              {/* 예약 정보 */}
              <div className="space-y-2 text-xs">
                {[
                  ["확인번호", <span key="c" className="font-mono text-slate-300">{selected.confirmation_number}</span>],
                  ["호텔", selected.hotel],
                  ["도착일", selected.arrival_date],
                  ["퇴실일", selected.departure_date],
                  ["박수", `${selected.nights}박`],
                  ["인원", `${selected.adults}명`],
                  ["룸", selected.room_type_assigned],
                  ["식사", selected.meal_plan],
                  ["1박 요금", `€${selected.rate_per_night.toFixed(0)}`],
                  ["총액", `€${selected.total_amount.toFixed(0)}`],
                ].map(([label, value]) => (
                  <div key={String(label)} className="flex justify-between">
                    <span className="text-slate-600">{label}</span>
                    <span className="text-slate-300">{value}</span>
                  </div>
                ))}
              </div>

              {/* 요금제 */}
              <FlexiBadge type={selected.pricing_type} discount={selected.discount_applied} />

              {/* DSS 링크 */}
              {selected.dss_booking_id && (
                <Link
                  href={`/dashboard/reservations/${selected.dss_booking_id}`}
                  className="block w-full text-center text-xs py-2 rounded-lg transition-colors text-blue-400 hover:text-blue-300"
                  style={{ backgroundColor: "#3B82F611", border: "1px solid #3B82F622" }}
                >
                  DSS 위험도 분석 보기 →
                </Link>
              )}
            </div>
          );
        })()}
      </div>
    </div>
  );
}
