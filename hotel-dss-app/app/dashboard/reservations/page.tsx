"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { listBookings } from "@/lib/api";
import type { BookingListItem } from "@/types/api";
import { formatDiscount } from "@/types/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

// ── Helpers ────────────────────────────────────────────────────────

type SortKey = keyof Pick<
  BookingListItem,
  "booking_id" | "hotel" | "country" | "arrival_date" | "nights" | "risk_score"
>;

type TimeFilter = "today" | "week" | "month" | "all";

function riskColor(score: number) {
  return score >= 0.7
    ? "var(--risk-high)"
    : score >= 0.4
      ? "var(--risk-medium)"
      : "var(--risk-low)";
}

function getRiskColor(score: number): string {
  if (score >= 0.7) return "var(--risk-high)";
  if (score >= 0.4) return "var(--risk-medium)";
  return "var(--risk-low)";
}

function calcLeadTime(arrivalDate: string): number {
  return Math.ceil((new Date(arrivalDate).getTime() - Date.now()) / 86400000);
}

function filterByTime(bookings: BookingListItem[], filter: TimeFilter): BookingListItem[] {
  if (filter === "all") return bookings;
  const today = Date.now();
  const limits: Record<TimeFilter, number> = {
    today: 2,
    week: 7,
    month: 30,
    all: Infinity,
  };
  const maxDays = limits[filter];
  return bookings.filter((b) => {
    const d = Math.ceil((new Date(b.arrival_date).getTime() - today) / 86400000);
    return d >= 0 && d <= maxDays;
  });
}

function countHighRisk(bookings: BookingListItem[], filter: TimeFilter, threshold = 0.65): number {
  return filterByTime(bookings, filter).filter((b) => b.risk_score >= threshold).length;
}

function PricingBadge({ flexi }: { flexi: boolean }) {
  return flexi ? (
    <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium text-white bg-yellow-600">
      Flexi Rate
    </span>
  ) : (
    <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium text-white/60 bg-white/10">
      Standard Rate
    </span>
  );
}

// ── Component ──────────────────────────────────────────────────────

export default function ReservationsPage() {
  const [allBookings, setAllBookings] = useState<BookingListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("risk_score");
  const [sortAsc, setSortAsc] = useState(false);
  const [timeFilter, setTimeFilter] = useState<TimeFilter>("all");
  const [selectedBooking, setSelectedBooking] = useState<BookingListItem | null>(null);

  useEffect(() => {
    listBookings()
      .then((res) => {
        setAllBookings(res.bookings);
        setTotal(res.total);
        setError(null);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Unknown error"));
  }, []);

  function handleSort(key: SortKey) {
    if (sortKey === key) {
      setSortAsc((v) => !v);
    } else {
      setSortKey(key);
      setSortAsc(true);
    }
  }

  const filtered = useMemo(() => {
    const byTime = filterByTime(allBookings, timeFilter);
    const q = query.trim().toLowerCase();
    const list = q
      ? byTime.filter(
          (b) =>
            b.booking_id.toLowerCase().includes(q) ||
            b.country.toLowerCase().includes(q)
        )
      : byTime;

    return [...list].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      let cmp = 0;
      if (typeof av === "number" && typeof bv === "number") {
        cmp = av - bv;
      } else {
        cmp = String(av).localeCompare(String(bv));
      }
      return sortAsc ? cmp : -cmp;
    });
  }, [allBookings, timeFilter, query, sortKey, sortAsc]);

  function SortIndicator({ colKey }: { colKey: SortKey }) {
    if (sortKey !== colKey) return <span className="text-white/20 ml-1">↕</span>;
    return <span className="ml-1">{sortAsc ? "↑" : "↓"}</span>;
  }

  const COLUMNS: { key: SortKey; label: string }[] = [
    { key: "booking_id", label: "Booking ID" },
    { key: "hotel", label: "Hotel" },
    { key: "country", label: "Country" },
    { key: "arrival_date", label: "Arrival" },
    { key: "nights", label: "Nights" },
    { key: "risk_score", label: "Risk Score" },
  ];

  return (
    <div className="p-6 space-y-4 text-white">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Reservations</h1>
          <p className="text-xs text-white/40 mt-0.5">총 {total}건</p>
        </div>
      </div>

      {error && (
        <div className="rounded-md bg-red-900/40 border border-red-500/40 px-4 py-2 text-sm text-red-300">
          API 오류: {error}
        </div>
      )}

      <div className="flex gap-4">
        {/* 메인 테이블 영역 */}
        <div className="flex-1 min-w-0">
          {/* 시간 탭 */}
          <div className="flex items-center gap-1 mb-3">
            {(["today", "week", "month", "all"] as TimeFilter[]).map((f) => {
              const labels: Record<TimeFilter, string> = {
                today: "오늘·내일",
                week: "이번 주",
                month: "이번 달",
                all: "전체",
              };
              const count = f !== "all" ? countHighRisk(allBookings, f) : null;
              return (
                <button
                  key={f}
                  onClick={() => setTimeFilter(f)}
                  className={[
                    "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
                    timeFilter === f
                      ? "bg-white/10 text-white"
                      : "text-white/40 hover:text-white/70 hover:bg-white/5",
                  ].join(" ")}
                >
                  {labels[f]}
                  {count !== null && count > 0 && (
                    <span className="rounded-full bg-red-500/80 px-1.5 py-0.5 text-[10px] font-bold text-white leading-none">
                      {count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Search */}
          <div className="flex items-center gap-3 mb-4">
            <input
              type="text"
              placeholder="Booking ID 또는 Country 검색..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-72 rounded-md border border-white/15 bg-white/5 px-3 py-1.5 text-sm text-white placeholder:text-white/30 focus:outline-none focus:ring-1 focus:ring-white/30"
            />
            {query && (
              <span className="text-xs text-white/40">
                {filtered.length}건 표시
              </span>
            )}
          </div>

          <Card className="bg-[var(--bg-card)] border-white/10 text-white">
            <CardHeader>
              <CardTitle className="text-sm">전체 예약 목록</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow className="border-white/10 hover:bg-transparent">
                    {COLUMNS.map(({ key, label }) => (
                      <TableHead
                        key={key}
                        className="text-white/50 cursor-pointer select-none hover:text-white/80 transition-colors"
                        onClick={() => handleSort(key)}
                      >
                        {label}
                        <SortIndicator colKey={key} />
                      </TableHead>
                    ))}
                    <TableHead className="text-white/50">Pricing</TableHead>
                    <TableHead className="text-white/50">Discount</TableHead>
                    <TableHead className="w-8" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filtered.length === 0 ? (
                    <TableRow className="border-white/10">
                      <TableCell
                        colSpan={9}
                        className="text-center text-white/30 py-8"
                      >
                        {allBookings.length === 0 && !error
                          ? "데이터 로딩 중..."
                          : "검색 결과 없음"}
                      </TableCell>
                    </TableRow>
                  ) : (
                    filtered.map((b) => (
                      <TableRow
                        key={b.booking_id}
                        onClick={() =>
                          setSelectedBooking(
                            selectedBooking?.booking_id === b.booking_id ? null : b
                          )
                        }
                        className={[
                          "cursor-pointer group transition-colors",
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
                        <TableCell>
                          <div className="flex flex-col">
                            <span className="text-sm text-white/80">
                              {new Date(b.arrival_date).toLocaleDateString("en", {
                                month: "short",
                                day: "numeric",
                              })}
                            </span>
                            <span className="text-[10px] text-white/30">
                              {Math.ceil(
                                (new Date(b.arrival_date).getTime() - Date.now()) /
                                  86400000
                              )}
                              d
                            </span>
                          </div>
                        </TableCell>
                        <TableCell className="text-white/70 text-center">
                          {b.nights}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <span
                              className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium text-white tabular-nums"
                              style={{ backgroundColor: riskColor(b.risk_score) }}
                            >
                              {(b.risk_score * 100).toFixed(1)}%
                            </span>
                            <div className="w-12 h-1 rounded-full bg-white/10 overflow-hidden">
                              <div
                                className="h-full rounded-full"
                                style={{
                                  width: `${b.risk_score * 100}%`,
                                  backgroundColor: riskColor(b.risk_score),
                                }}
                              />
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <PricingBadge flexi={b.flexi_recommended} />
                        </TableCell>
                        <TableCell className="text-white/60 text-xs">
                          {formatDiscount(b.discount_rate)}
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
            </CardContent>
          </Card>
        </div>

        {/* 상세 패널 */}
        {selectedBooking && (
          <div className="w-72 shrink-0 rounded-xl border border-white/10 bg-[var(--bg-card)] p-5 space-y-4 self-start sticky top-6">
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

            {/* 위험도 바 */}
            <div>
              <div className="flex justify-between items-center mb-1.5">
                <span className="text-xs text-white/40">취소 위험도</span>
                <span
                  className="text-sm font-bold tabular-nums"
                  style={{ color: getRiskColor(selectedBooking.risk_score) }}
                >
                  {Math.round(selectedBooking.risk_score * 100)}%
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
                    new Date(selectedBooking.arrival_date).toLocaleDateString("en", {
                      month: "short",
                      day: "numeric",
                    }),
                  ],
                  ["리드타임", `${calcLeadTime(selectedBooking.arrival_date)}일`],
                  ["숙박", `${selectedBooking.nights}박`],
                  ["인원", `${selectedBooking.adults}명`],
                ] as [string, React.ReactNode][]
              ).map(([label, value]) => (
                <div key={label as string} className="flex justify-between">
                  <span className="text-white/40">{label}</span>
                  <span className="text-white/80">{value}</span>
                </div>
              ))}
            </div>

            {/* Flexi 권장 */}
            {selectedBooking.flexi_recommended && (
              <div className="rounded-lg bg-yellow-500/10 border border-yellow-500/20 p-3">
                <p className="text-xs font-semibold text-yellow-400">
                  Flexi 라우팅 권장
                </p>
                <p className="text-xs text-yellow-400/60 mt-1">
                  {selectedBooking.discount_rate
                    ? `할인율 ${Math.round(selectedBooking.discount_rate * 100)}% 적용`
                    : ""}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
