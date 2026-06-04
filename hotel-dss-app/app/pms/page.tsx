"use client";

import { useEffect, useState } from "react";
import { getPMSReservations, getPMSActivity, getPMSStats } from "@/lib/pms-api";
import type { PMSReservationRecord, PMSActivityEvent, PMSStats } from "@/types/pms";
import { PERSONAS, PERSONA_BY_ID, getRiskTendencyColor } from "@/types/pms";
import Link from "next/link";

// ── 아바타 컴포넌트 ──────────────────────────────────────────
function Avatar({ initials, color, size = 36 }: { initials: string; color: string; size?: number }) {
  return (
    <div
      className="flex items-center justify-center rounded-full font-bold text-white shrink-0"
      style={{
        width: size,
        height: size,
        backgroundColor: color + "33",
        border: `2px solid ${color}55`,
        fontSize: size * 0.33,
        color: color,
      }}
    >
      {initials}
    </div>
  );
}

// ── 활동 이벤트 아이콘 ──────────────────────────────────────
function ActionIcon({ action }: { action: PMSActivityEvent["action"] }) {
  const icons: Record<string, string> = {
    thinking: "💭",
    booking:  "📝",
    confirmed:"✅",
    error:    "❌",
  };
  return <span className="text-sm">{icons[action] ?? "•"}</span>;
}

// ── Flexi 배지 ──────────────────────────────────────────────
function FlexiBadge({ type, discount }: { type: string; discount: number | null }) {
  if (type === "Flexi Rate") {
    return (
      <span
        className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold"
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

export default function PMSDashboard() {
  const [stats, setStats] = useState<PMSStats | null>(null);
  const [reservations, setReservations] = useState<PMSReservationRecord[]>([]);
  const [activity, setActivity] = useState<PMSActivityEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState<boolean | null>(null);

  useEffect(() => {
    async function fetchAll() {
      try {
        const [s, r, a] = await Promise.all([
          getPMSStats(),
          getPMSReservations(),
          getPMSActivity(30),
        ]);
        setStats(s);
        setReservations(r.reservations.slice(0, 10));
        setActivity(a.events);
        setConnected(true);
        setError(null);
      } catch (e) {
        setConnected(false);
        setError(e instanceof Error ? e.message : "PMS 서버 연결 실패");
      }
    }

    fetchAll();
    const timer = setInterval(fetchAll, 2000);  // 2초마다 polling
    return () => clearInterval(timer);
  }, []);

  // 각 페르소나의 최신 예약
  const personaLastBooking: Record<string, PMSReservationRecord> = {};
  for (const r of reservations) {
    if (!personaLastBooking[r.agent_id]) {
      personaLastBooking[r.agent_id] = r;
    }
  }

  return (
    <div className="p-6 space-y-6 text-white min-h-screen">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">PMS Dashboard</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Property Management System — Guest Reservations
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div
            className="w-2 h-2 rounded-full animate-pulse"
            style={{ backgroundColor: connected ? "#34D399" : "#FB7185" }}
          />
          <span className="text-[11px] text-slate-500">
            {connected === null ? "연결 중..." : connected ? "PMS :3001 연결됨" : "PMS 서버 오프라인"}
          </span>
        </div>
      </div>

      {/* 오류 배너 */}
      {error && (
        <div className="rounded-lg px-4 py-3 text-sm bg-red-500/10 border border-red-500/30 text-red-400">
          {error} — PMS 서버를 시작하세요:{" "}
          <code className="text-[11px] bg-red-500/10 px-1 rounded">
            uvicorn app_pms.pms_mock:app --port 3001 --reload
          </code>
        </div>
      )}

      {/* KPI 카드 */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "전체 예약", value: stats?.total_reservations ?? 0, color: "#94A3B8" },
          { label: "Flexi 라우팅", value: stats?.flexi_count ?? 0, color: "#F59E0B" },
          { label: "Standard", value: stats?.standard_count ?? 0, color: "#34D399" },
          { label: "활성 게스트", value: stats?.unique_agents ?? 0, color: "#3B82F6" },
        ].map(({ label, value, color }) => (
          <div
            key={label}
            className="rounded-xl border border-slate-800 bg-slate-900 p-4"
          >
            <p className="text-xs text-slate-500">{label}</p>
            <p className="text-3xl font-bold mt-1" style={{ color }}>
              {value}
            </p>
          </div>
        ))}
      </div>

      {/* 메인 레이아웃: 페르소나 + 활동 피드 */}
      <div className="grid grid-cols-5 gap-4">
        {/* 게스트 페르소나 카드 (2/5) */}
        <div className="col-span-2 space-y-3">
          <h2 className="text-sm font-semibold text-slate-300">
            Guest Profiles
            <span className="ml-2 text-xs text-slate-600 font-normal">LLM 에이전트 페르소나</span>
          </h2>
          {PERSONAS.map((persona) => {
            const lastBook = personaLastBooking[persona.id];
            return (
              <div
                key={persona.id}
                className="rounded-xl border border-slate-800 bg-slate-900 p-4 transition-all"
                style={
                  lastBook
                    ? { borderColor: persona.avatar_color + "44" }
                    : {}
                }
              >
                <div className="flex items-start gap-3">
                  <Avatar initials={persona.avatar_initials} color={persona.avatar_color} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-white">{persona.name}</span>
                      <span className="text-base">{persona.flag}</span>
                    </div>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-[11px] text-slate-500">{persona.persona_type}</span>
                      <span className="text-[10px] text-slate-700">·</span>
                      <span
                        className="text-[10px] font-medium"
                        style={{ color: getRiskTendencyColor(persona.risk_tendency) }}
                      >
                        {persona.risk_tendency === "high" ? "취소 위험 높음" :
                         persona.risk_tendency === "medium" ? "취소 위험 보통" : "취소 위험 낮음"}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-600 mt-1 leading-relaxed line-clamp-2">
                      {persona.description}
                    </p>
                  </div>
                </div>
                {/* 가장 최근 예약 */}
                {lastBook && (
                  <div className="mt-3 pt-3 border-t border-slate-800 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[11px] text-slate-400">
                        {lastBook.confirmation_number}
                      </span>
                      <span className="text-[10px] text-slate-600">{lastBook.hotel.replace(" Hotel", "")}</span>
                    </div>
                    <FlexiBadge
                      type={lastBook.pricing_type}
                      discount={lastBook.discount_applied}
                    />
                  </div>
                )}
                {!lastBook && (
                  <div className="mt-3 pt-3 border-t border-slate-800">
                    <span className="text-[11px] text-slate-700">아직 예약 없음 — 시뮬레이션 실행 대기</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* 실시간 활동 피드 (3/5) */}
        <div className="col-span-3 rounded-xl border border-slate-800 bg-slate-900 overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-300">Live Agent Activity</h2>
            <div className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
              <span className="text-[11px] text-slate-600">2초 polling</span>
            </div>
          </div>

          {/* 터미널 스타일 로그 */}
          <div
            className="p-4 space-y-2 font-mono text-xs overflow-y-auto"
            style={{ maxHeight: "520px", backgroundColor: "#020617" }}
          >
            {activity.length === 0 ? (
              <div className="text-slate-700 space-y-1">
                <p className="text-slate-600">$ 에이전트 대기 중...</p>
                <p className="text-slate-700">시뮬레이션을 시작하려면:</p>
                <p className="text-green-700">  python -m llm_sim.run_simulation</p>
                <p className="text-slate-700 mt-2">또는 특정 에이전트만:</p>
                <p className="text-green-700">  python -m llm_sim.run_simulation --agents ana paulo</p>
              </div>
            ) : (
              activity.map((event) => {
                const persona = PERSONA_BY_ID[event.agent_id];
                const color = persona?.avatar_color ?? "#94A3B8";
                const timeStr = new Date(event.timestamp).toLocaleTimeString("ko", {
                  hour: "2-digit", minute: "2-digit", second: "2-digit"
                });
                return (
                  <div
                    key={event.event_id}
                    className="flex gap-2 items-start py-1 border-b border-slate-900/50"
                  >
                    <span className="text-slate-700 shrink-0 tabular-nums">{timeStr}</span>
                    <ActionIcon action={event.action} />
                    <div className="flex-1 min-w-0">
                      <span
                        className="font-semibold mr-1"
                        style={{ color }}
                      >
                        [{event.persona_name}]
                      </span>
                      <span className="text-slate-400">{event.message}</span>
                      {event.confirmation_number && (
                        <span className="ml-2 text-slate-600">
                          → <span style={{ color }} className="font-semibold">{event.confirmation_number}</span>
                        </span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* 최근 예약 테이블 */}
      <div className="rounded-xl border border-slate-800 bg-slate-900 overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-300">
            Recent Reservations
            <span className="ml-2 text-xs text-slate-600 font-normal">최근 10건</span>
          </h2>
          <Link
            href="/pms/reservations"
            className="text-[11px] text-slate-600 hover:text-blue-400 transition-colors"
          >
            전체 보기 →
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-slate-800">
                {["확인번호", "게스트", "호텔", "도착일", "박수", "요금제", "금액", "DSS 위험도"].map(h => (
                  <th key={h} className="px-4 py-2.5 text-left text-slate-600 font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {reservations.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-slate-700">
                    예약 데이터가 없습니다 — 시뮬레이션을 실행하세요
                  </td>
                </tr>
              ) : (
                reservations.map((r) => {
                  const persona = PERSONA_BY_ID[r.agent_id];
                  return (
                    <tr key={r.confirmation_number} className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors">
                      <td className="px-4 py-3 font-mono text-slate-300">{r.confirmation_number}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          {persona && (
                            <Avatar initials={persona.avatar_initials} color={persona.avatar_color} size={26} />
                          )}
                          <div>
                            <p className="text-slate-200 font-medium">{r.persona_name}</p>
                            <p className="text-slate-600 text-[10px]">{r.persona_type} · {r.persona_nationality}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-slate-400">{r.hotel.replace(" Hotel", "")}</td>
                      <td className="px-4 py-3 text-slate-400">{r.arrival_date}</td>
                      <td className="px-4 py-3 text-slate-400">{r.nights}박</td>
                      <td className="px-4 py-3">
                        <FlexiBadge type={r.pricing_type} discount={r.discount_applied} />
                      </td>
                      <td className="px-4 py-3 text-slate-300 font-mono">
                        €{r.total_amount.toFixed(0)}
                      </td>
                      <td className="px-4 py-3">
                        {r.dss_risk_score !== null ? (
                          <div className="flex items-center gap-2">
                            <span
                              className="font-mono font-semibold"
                              style={{
                                color: r.dss_risk_score >= 0.7 ? "#FB7185"
                                     : r.dss_risk_score >= 0.4 ? "#FBBF24"
                                     : "#34D399"
                              }}
                            >
                              {(r.dss_risk_score * 100).toFixed(1)}%
                            </span>
                            {r.dss_booking_id && (
                              <Link
                                href={`/dashboard/reservations/${r.dss_booking_id}`}
                                className="text-[10px] text-slate-700 hover:text-blue-400 transition-colors"
                              >
                                DSS →
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
      </div>

      {/* 시뮬레이션 실행 가이드 */}
      {reservations.length === 0 && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6 text-center space-y-3">
          <p className="text-slate-500 text-sm">LLM 에이전트 시뮬레이션을 실행하면</p>
          <p className="text-slate-600 text-xs">5명의 게스트 페르소나가 실제 Claude API를 통해 예약을 생성합니다</p>
          <div className="bg-slate-900 rounded-lg px-4 py-3 font-mono text-xs text-green-600 inline-block mt-2">
            python -m llm_sim.run_simulation
          </div>
        </div>
      )}
    </div>
  );
}
