"use client"
import { useState } from "react"
import { createBooking } from "@/lib/api"
import type {
  BookingRequest,
  BookingResponse,
  HotelType,
  ChannelType,
  MarketSegmentType,
  RoomType,
  MealType,
  CustomerType,
} from "@/types/api"
import DomainInbox from "./domain-inbox"
import AutoFeedDemo from "./auto-feed-demo"

type NewBookingView = "form" | "autofeed" | "inbox"

const inputCls =
  "w-full rounded-lg border border-white/10 bg-[#18181B] px-3 py-2.5 text-sm text-white focus:outline-none focus:border-white/30"
const selectCls =
  "w-full rounded-lg border border-white/10 bg-[#18181B] px-3 py-2.5 text-sm text-white focus:outline-none focus:border-white/30 appearance-none cursor-pointer pr-8"
const labelCls = "text-xs text-white/50 mb-1.5 block"
const groupCls =
  "rounded-xl border border-white/10 bg-[var(--bg-card)] p-5 space-y-4"
const groupTitleCls =
  "text-xs font-semibold text-white/60 uppercase tracking-wider"

const INITIAL_FORM = {
  hotel: "City Hotel" as HotelType,
  arrival_date: "",
  departure_date: "",
  adults: 2,
  children: 0,
  babies: 0,
  distribution_channel: "Direct" as ChannelType,
  market_segment: "Direct" as MarketSegmentType,
  reserved_room_type: "D" as RoomType,
  meal: "BB" as MealType,
  country: "GBR",
  customer_type: "Transient" as CustomerType,
  adr: 120,
  is_repeated_guest: 0 as 0 | 1,
  previous_cancellations: 0,
  booking_changes: 0,
  required_car_parking_spaces: 0,
  total_of_special_requests: 0,
}

function NewBookingForm() {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<BookingResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [form, setForm] = useState(INITIAL_FORM)

  function set<K extends keyof typeof INITIAL_FORM>(
    key: K,
    value: (typeof INITIAL_FORM)[K]
  ) {
    setForm((f) => ({ ...f, [key]: value }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!form.arrival_date || !form.departure_date) {
      setError("도착일과 출발일을 입력해주세요.")
      return
    }
    if (form.departure_date <= form.arrival_date) {
      setError("출발일은 도착일보다 이후여야 합니다.")
      return
    }
    setLoading(true)
    setError(null)
    try {
      const payload: BookingRequest = {
        hotel: form.hotel,
        arrival_date: form.arrival_date,
        departure_date: form.departure_date,
        adults: form.adults,
        children: form.children,
        babies: form.babies,
        distribution_channel: form.distribution_channel,
        market_segment: form.market_segment,
        reserved_room_type: form.reserved_room_type,
        meal: form.meal,
        country: form.country,
        customer_type: form.customer_type,
        adr: form.adr,
        is_repeated_guest: form.is_repeated_guest,
        previous_cancellations: form.previous_cancellations,
        booking_changes: form.booking_changes,
        required_car_parking_spaces: form.required_car_parking_spaces,
        total_of_special_requests: form.total_of_special_requests,
      }
      const res = await createBooking(payload)
      setResult(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : "오류가 발생했습니다.")
    } finally {
      setLoading(false)
    }
  }

  const today = new Date().toISOString().split("T")[0]

  return (
    <div className="max-w-2xl">
      {/* 헤더 */}
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-white">신규 예약 위험도 평가</h1>
        <p className="text-xs text-white/40 mt-0.5">
          예약 정보 입력 후 AI 취소 위험도를 즉시 확인
        </p>
      </div>

      {/* 에러 배너 */}
      {error && (
        <div className="mb-4 rounded-lg bg-red-900/30 border border-red-500/30 px-4 py-2 text-sm text-red-300">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* ── 그룹 1: 체류 정보 ─────────────────────────── */}
        <div className={groupCls}>
          <h2 className={groupTitleCls}>체류 정보</h2>

          {/* 호텔 토글 */}
          <div>
            <label className={labelCls}>호텔</label>
            <div className="flex gap-2">
              {(["City Hotel", "Resort Hotel"] as const).map((h) => (
                <button
                  key={h}
                  type="button"
                  onClick={() => set("hotel", h)}
                  className={[
                    "flex-1 py-2 rounded-lg text-sm font-medium transition-all",
                    form.hotel === h
                      ? "bg-white text-black font-semibold border border-transparent"
                      : "bg-white/5 text-white/50 border border-white/10 hover:bg-white/10 hover:text-white/80",
                  ].join(" ")}
                >
                  {h}
                </button>
              ))}
            </div>
          </div>

          {/* 날짜 */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelCls}>도착일</label>
              <input
                type="date"
                value={form.arrival_date}
                min={today}
                onChange={(e) => set("arrival_date", e.target.value)}
                className="w-full rounded-lg border border-white/10 bg-[#18181B] px-3 py-2.5 text-sm text-white [color-scheme:dark] focus:outline-none focus:border-white/30"
              />
            </div>
            <div>
              <label className={labelCls}>출발일</label>
              <input
                type="date"
                value={form.departure_date}
                min={form.arrival_date || today}
                onChange={(e) => set("departure_date", e.target.value)}
                className="w-full rounded-lg border border-white/10 bg-[#18181B] px-3 py-2.5 text-sm text-white [color-scheme:dark] focus:outline-none focus:border-white/30"
              />
            </div>
          </div>

          {/* 인원 */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelCls}>성인</label>
              <input
                type="number"
                min={1}
                max={9}
                value={form.adults}
                onChange={(e) =>
                  set("adults", Math.max(1, parseInt(e.target.value) || 1))
                }
                className={inputCls}
              />
            </div>
            <div>
              <label className={labelCls}>아동</label>
              <input
                type="number"
                min={0}
                max={5}
                value={form.children}
                onChange={(e) =>
                  set("children", Math.max(0, parseInt(e.target.value) || 0))
                }
                className={inputCls}
              />
            </div>
          </div>
        </div>

        {/* ── 그룹 2: 예약 채널 ─────────────────────────── */}
        <div className={groupCls}>
          <h2 className={groupTitleCls}>예약 채널</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelCls}>채널</label>
              <div className="relative">
                <select
                  value={form.distribution_channel}
                  onChange={(e) =>
                    set("distribution_channel", e.target.value as ChannelType)
                  }
                  className={selectCls}
                >
                  <option value="Direct">Direct</option>
                  <option value="Corporate">Corporate</option>
                  <option value="TA/TO">TA/TO (OTA)</option>
                  <option value="GDS">GDS</option>
                  <option value="Undefined">Undefined</option>
                </select>
                <div className="pointer-events-none absolute inset-y-0 right-3 flex items-center">
                  <svg className="w-3.5 h-3.5 text-white/40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </div>
            </div>

            <div>
              <label className={labelCls}>마켓 세그먼트</label>
              <div className="relative">
                <select
                  value={form.market_segment}
                  onChange={(e) =>
                    set(
                      "market_segment",
                      e.target.value as MarketSegmentType
                    )
                  }
                  className={selectCls}
                >
                  <option value="Direct">Direct</option>
                  <option value="Corporate">Corporate</option>
                  <option value="Online TA">Online TA</option>
                  <option value="Offline TA/TO">Offline TA/TO</option>
                  <option value="Groups">Groups</option>
                  <option value="Complementary">Complementary</option>
                  <option value="Aviation">Aviation</option>
                </select>
                <div className="pointer-events-none absolute inset-y-0 right-3 flex items-center">
                  <svg className="w-3.5 h-3.5 text-white/40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </div>
            </div>

            <div>
              <label className={labelCls}>고객 유형</label>
              <div className="relative">
                <select
                  value={form.customer_type}
                  onChange={(e) =>
                    set("customer_type", e.target.value as CustomerType)
                  }
                  className={selectCls}
                >
                  <option value="Transient">Transient</option>
                  <option value="Contract">Contract</option>
                  <option value="Transient-Party">Transient-Party</option>
                  <option value="Group">Group</option>
                </select>
                <div className="pointer-events-none absolute inset-y-0 right-3 flex items-center">
                  <svg className="w-3.5 h-3.5 text-white/40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </div>
            </div>

            <div>
              <label className={labelCls}>ADR (EUR/박)</label>
              <input
                type="number"
                min={0}
                step={10}
                value={form.adr}
                onChange={(e) =>
                  set("adr", Math.max(0, parseFloat(e.target.value) || 0))
                }
                className={inputCls}
              />
            </div>
          </div>
        </div>

        {/* ── 그룹 3: 객실·식사 ─────────────────────────── */}
        <div className={groupCls}>
          <h2 className={groupTitleCls}>객실 · 식사</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelCls}>객실 유형</label>
              <div className="relative">
                <select
                  value={form.reserved_room_type}
                  onChange={(e) =>
                    set("reserved_room_type", e.target.value as RoomType)
                  }
                  className={selectCls}
                >
                  <option value="A">A - Standard</option>
                  <option value="B">B - Standard Plus</option>
                  <option value="C">C - Superior</option>
                  <option value="D">D - Deluxe</option>
                  <option value="E">E - Executive</option>
                  <option value="F">F - Junior Suite</option>
                  <option value="G">G - Suite</option>
                  <option value="H">H - Family</option>
                  <option value="L">L - Presidential</option>
                </select>
                <div className="pointer-events-none absolute inset-y-0 right-3 flex items-center">
                  <svg className="w-3.5 h-3.5 text-white/40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </div>
            </div>

            <div>
              <label className={labelCls}>식사 플랜</label>
              <div className="relative">
                <select
                  value={form.meal}
                  onChange={(e) => set("meal", e.target.value as MealType)}
                  className={selectCls}
                >
                  <option value="BB">BB - Bed &amp; Breakfast</option>
                  <option value="HB">HB - Half Board</option>
                  <option value="FB">FB - Full Board</option>
                  <option value="SC">SC - Room Only</option>
                </select>
                <div className="pointer-events-none absolute inset-y-0 right-3 flex items-center">
                  <svg className="w-3.5 h-3.5 text-white/40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ── 그룹 4: 고객 정보 ─────────────────────────── */}
        <div className={groupCls}>
          <h2 className={groupTitleCls}>고객 정보</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelCls}>국적 (ISO 3자리)</label>
              <div className="relative">
                <select
                  value={form.country}
                  onChange={(e) => set("country", e.target.value)}
                  className={selectCls}
                >
                  <option value="PRT">PRT - Portugal</option>
                  <option value="GBR">GBR - United Kingdom</option>
                  <option value="FRA">FRA - France</option>
                  <option value="ESP">ESP - Spain</option>
                  <option value="DEU">DEU - Germany</option>
                  <option value="IRL">IRL - Ireland</option>
                  <option value="BEL">BEL - Belgium</option>
                  <option value="BRA">BRA - Brazil</option>
                  <option value="NLD">NLD - Netherlands</option>
                  <option value="ITA">ITA - Italy</option>
                  <option value="USA">USA - United States</option>
                  <option value="CHN">CHN - China</option>
                  <option value="JPN">JPN - Japan</option>
                  <option value="KOR">KOR - South Korea</option>
                  <option value="AUS">AUS - Australia</option>
                </select>
                <div className="pointer-events-none absolute inset-y-0 right-3 flex items-center">
                  <svg className="w-3.5 h-3.5 text-white/40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </div>
            </div>

            <div>
              <label className={labelCls}>과거 취소 횟수</label>
              <input
                type="number"
                min={0}
                max={10}
                value={form.previous_cancellations}
                onChange={(e) =>
                  set(
                    "previous_cancellations",
                    Math.max(0, parseInt(e.target.value) || 0)
                  )
                }
                className={inputCls}
              />
            </div>
          </div>

          {/* 특별 요청 슬라이더 */}
          <div>
            <label className={labelCls}>
              특별 요청 수:{" "}
              <span className="text-white">{form.total_of_special_requests}</span>
            </label>
            <input
              type="range"
              min={0}
              max={5}
              value={form.total_of_special_requests}
              onChange={(e) =>
                set("total_of_special_requests", parseInt(e.target.value))
              }
              className="w-full accent-white/60"
            />
            <div className="flex justify-between text-[10px] text-white/30 mt-1">
              <span>0</span>
              <span>5</span>
            </div>
          </div>
        </div>

        {/* 제출 버튼 */}
        <button
          type="submit"
          disabled={loading}
          className="w-full py-3 rounded-xl bg-white text-black text-sm font-semibold hover:bg-white/90 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? "분석 중..." : "위험도 평가 실행"}
        </button>
      </form>

      {/* ── 결과 모달 ─────────────────────────────────── */}
      {result && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-6">
          <div className="w-full max-w-md rounded-2xl border border-white/10 bg-[#1C1E26] p-6 shadow-2xl">
            {/* 모달 헤더 */}
            <div className="flex items-start justify-between mb-5">
              <div>
                <h2 className="text-base font-semibold text-white">
                  위험도 평가 완료
                </h2>
                <p className="text-xs text-white/40 mt-0.5 font-mono">
                  {result.booking_id}
                </p>
              </div>
              <button
                onClick={() => setResult(null)}
                className="text-white/30 hover:text-white/70 text-xl leading-none transition-colors"
              >
                ×
              </button>
            </div>

            {/* 위험도 게이지 */}
            <div className="mb-5">
              <div className="flex justify-between items-end mb-2">
                <span className="text-xs text-white/40">취소 위험도</span>
                <span
                  className="text-3xl font-bold tabular-nums"
                  style={{
                    color:
                      result.risk_score >= 0.7
                        ? "var(--risk-high)"
                        : result.risk_score >= 0.4
                        ? "var(--risk-medium)"
                        : "var(--risk-low)",
                  }}
                >
                  {Math.round(result.risk_score * 100)}%
                </span>
              </div>
              <div className="h-2.5 rounded-full bg-white/10 overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-700"
                  style={{
                    width: `${result.risk_score * 100}%`,
                    backgroundColor:
                      result.risk_score >= 0.7
                        ? "var(--risk-high)"
                        : result.risk_score >= 0.4
                        ? "var(--risk-medium)"
                        : "var(--risk-low)",
                  }}
                />
              </div>
              <div className="flex justify-between text-[10px] text-white/30 mt-1">
                <span>저위험</span>
                <span className="text-yellow-400/60">임계값 65%</span>
                <span>고위험</span>
              </div>
            </div>

            {/* Flexi 결정 배너 */}
            {result.flexi_recommended ? (
              <div className="rounded-xl bg-yellow-500/10 border border-yellow-500/25 p-4 mb-4">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-yellow-400 text-base">&#9889;</span>
                  <span className="text-sm font-semibold text-yellow-300">
                    Flexi Rate 배정 권장
                  </span>
                </div>
                <p className="text-xs text-yellow-400/70">
                  할인율{" "}
                  {result.discount_rate != null
                    ? `${Math.round(result.discount_rate * 100)}%`
                    : "—"}{" "}
                  적용 시 취소 위험 완화 기대
                </p>
              </div>
            ) : (
              <div className="rounded-xl bg-emerald-500/10 border border-emerald-500/25 p-4 mb-4">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-emerald-400 text-base">&#10003;</span>
                  <span className="text-sm font-semibold text-emerald-300">
                    Standard Rate 배정
                  </span>
                </div>
                <p className="text-xs text-emerald-400/70">
                  낮은 취소 위험 — 일반 객실 배정
                </p>
              </div>
            )}

            {/* SHAP Top 3 요인 */}
            {result.top_risk_factors && result.top_risk_factors.length > 0 && (
              <div>
                <p className="text-xs text-white/40 mb-2">
                  주요 위험 요인 (SHAP)
                </p>
                <div className="space-y-1.5">
                  {result.top_risk_factors.map((f, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <span className="text-[10px] text-white/30 w-3">
                        {i + 1}
                      </span>
                      <div className="flex-1 rounded-lg bg-white/5 px-3 py-1.5">
                        <p className="text-xs text-white/70">{f.label}</p>
                      </div>
                      <span
                        className="text-xs tabular-nums font-mono w-14 text-right"
                        style={{
                          color:
                            f.shap_value > 0
                              ? "var(--risk-medium)"
                              : "var(--risk-low)",
                        }}
                      >
                        {f.shap_value > 0 ? "+" : ""}
                        {f.shap_value.toFixed(2)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 하단 버튼 */}
            <div className="flex gap-2 mt-5">
              <button
                onClick={() => {
                  setResult(null)
                  setForm((f) => ({
                    ...f,
                    arrival_date: "",
                    departure_date: "",
                  }))
                }}
                className="flex-1 py-2 rounded-lg bg-white/5 text-white/70 text-sm hover:bg-white/10 transition-all"
              >
                새 예약
              </button>
              <button
                onClick={() => setResult(null)}
                className="flex-1 py-2 rounded-lg bg-white text-black text-sm font-semibold hover:bg-white/90 transition-all"
              >
                확인
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ── 페이지: [신규 입력 | 도메인 인박스] 뷰 토글 ──────────────────────────
export default function NewBookingPage() {
  const [view, setView] = useState<NewBookingView>("form")

  const TABS: { key: NewBookingView; label: string }[] = [
    { key: "form", label: "신규 입력" },
    { key: "autofeed", label: "자동 유입 데모" },
    { key: "inbox", label: "도메인 인박스" },
  ]

  return (
    <div className="p-6 text-white">
      {/* 뷰 토글 */}
      <div className="mb-6 flex items-center gap-1">
        {TABS.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setView(key)}
            className={[
              "px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
              view === key
                ? "bg-white/10 text-white"
                : "text-white/40 hover:text-white/70 hover:bg-white/5",
            ].join(" ")}
          >
            {label}
          </button>
        ))}
      </div>

      {view === "form" ? <NewBookingForm /> : view === "autofeed" ? <AutoFeedDemo /> : <DomainInbox />}
    </div>
  )
}
