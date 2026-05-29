"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getFlexiPreview, listBookings } from "@/lib/api";
import type { FlexiPreview, BookingListItem } from "@/types/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatRiskScore, formatDiscount } from "@/types/api";

// ── Debounce hook ──────────────────────────────────────────────────
function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState<T>(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

// ── Stat card ─────────────────────────────────────────────────────
function StatCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string | number;
  sub?: string;
  accent?: string;
}) {
  return (
    <Card className="bg-[var(--bg-card)] border-white/10 text-white">
      <CardHeader>
        <CardTitle className="text-xs text-white/50 font-normal">
          {label}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <span
          className="text-2xl font-bold"
          style={accent ? { color: accent } : undefined}
        >
          {value}
        </span>
        {sub && <p className="text-xs text-white/40 mt-1">{sub}</p>}
      </CardContent>
    </Card>
  );
}

// ── Main ──────────────────────────────────────────────────────────
export default function FlexiPolicyPage() {
  const [threshold, setThreshold] = useState(0.65);
  const debouncedThreshold = useDebounce(threshold, 300);
  const [preview, setPreview] = useState<FlexiPreview | null>(null);
  const [flexiBookings, setFlexiBookings] = useState<BookingListItem[]>([]);
  const [previewError, setPreviewError] = useState<string | null>(null);

  // Fetch flexi preview when debounced threshold changes
  useEffect(() => {
    getFlexiPreview(debouncedThreshold)
      .then((p) => {
        setPreview(p);
        setPreviewError(null);
      })
      .catch((e) =>
        setPreviewError(e instanceof Error ? e.message : "Unknown error")
      );
  }, [debouncedThreshold]);

  // Re-fetch flexi-routed bookings when threshold changes
  // (pool membership changes with threshold — keep table in sync)
  useEffect(() => {
    listBookings({ min_risk: debouncedThreshold })
      .then((res) => setFlexiBookings(res.bookings))
      .catch(() => {});
  }, [debouncedThreshold]);

  function handleSliderChange(value: number | readonly number[]) {
    const v = Array.isArray(value) ? value[0] : value;
    setThreshold(Math.round((v as number) * 100) / 100);
  }

  const walkImprove = preview
    ? preview.walk_rate_improvement * 100
    : null;

  return (
    <div className="p-6 space-y-6 text-white">
      <div>
        <h1 className="text-xl font-semibold">Flexi Policy</h1>
        <p className="text-xs text-white/40 mt-0.5">
          임계값 조정 → Pool Size / Walk Rate 실시간 미리보기
        </p>
      </div>

      {previewError && (
        <div className="rounded-md bg-red-900/40 border border-red-500/40 px-4 py-2 text-sm text-red-300">
          API 오류: {previewError}
        </div>
      )}

      {/* Threshold Slider Card */}
      <Card className="bg-[var(--bg-card)] border-white/10 text-white">
        <CardHeader>
          <CardTitle className="text-sm flex items-center justify-between">
            <span>취소 위험도 임계값</span>
            <span
              className="text-xl font-bold tabular-nums"
              style={{ color: "var(--risk-medium)" }}
            >
              {(threshold * 100).toFixed(0)}%
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Slider
            min={0.5}
            max={0.85}
            step={0.01}
            value={[threshold]}
            onValueChange={handleSliderChange}
            className="w-full"
          />
          <div className="flex justify-between text-xs text-white/40">
            <span>50% (공격적)</span>
            <span>85% (보수적)</span>
          </div>
        </CardContent>
      </Card>

      {/* KPI Preview */}
      <div className="grid grid-cols-3 gap-4">
        <StatCard
          label="Flexi Pool Size"
          value={preview?.estimated_pool_size ?? "—"}
          sub="임계값 초과 예약 수"
          accent="#3B82F6"
        />
        <StatCard
          label="예상 Walk Rate"
          value={
            preview
              ? `${(preview.estimated_walk_rate * 100).toFixed(1)}%`
              : "—"
          }
          sub={
            preview
              ? `기준선 ${(preview.baseline_walk_rate * 100).toFixed(1)}%`
              : undefined
          }
          accent={
            preview && preview.estimated_walk_rate < 0.02
              ? "var(--risk-low)"
              : "var(--risk-medium)"
          }
        />
        <StatCard
          label="Walk Rate 개선"
          value={
            walkImprove !== null
              ? `${walkImprove >= 0 ? "+" : ""}${walkImprove.toFixed(1)}pp`
              : "—"
          }
          sub={
            preview && preview.walk_rate_improvement > 0
              ? "현재 임계값으로 개선됨"
              : "개선 없음"
          }
          accent={
            walkImprove !== null && walkImprove > 0
              ? "var(--risk-low)"
              : "var(--risk-high)"
          }
        />
      </div>

      {/* Flexi-Routed Bookings Table */}
      <Card className="bg-[var(--bg-card)] border-white/10 text-white">
        <CardHeader>
          <CardTitle className="text-sm">
            Flexi 라우팅 완료 예약 목록
            {flexiBookings.length > 0 && (
              <span className="ml-2 text-xs text-white/40 font-normal">
                {flexiBookings.length}건
              </span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="border-white/10 hover:bg-transparent">
                <TableHead className="text-white/50">Booking ID</TableHead>
                <TableHead className="text-white/50">Hotel</TableHead>
                <TableHead className="text-white/50">Country</TableHead>
                <TableHead className="text-white/50">Arrival</TableHead>
                <TableHead className="text-white/50">Nights</TableHead>
                <TableHead className="text-white/50">Risk Score</TableHead>
                <TableHead className="text-white/50">Discount</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {flexiBookings.length === 0 ? (
                <TableRow className="border-white/10">
                  <TableCell
                    colSpan={7}
                    className="text-center text-white/30 py-8"
                  >
                    Flexi 라우팅된 예약 없음 (목업 서버 실행 시 표시)
                  </TableCell>
                </TableRow>
              ) : (
                flexiBookings.map((b) => (
                  <TableRow
                    key={b.booking_id}
                    className="border-white/10 hover:bg-white/5"
                  >
                    <TableCell className="font-mono text-xs text-white/80">
                      {b.booking_id}
                    </TableCell>
                    <TableCell className="text-white/70">{b.hotel}</TableCell>
                    <TableCell className="text-white/70">{b.country}</TableCell>
                    <TableCell className="text-white/70">
                      {b.arrival_date}
                    </TableCell>
                    <TableCell className="text-white/70 text-center">
                      {b.nights}
                    </TableCell>
                    <TableCell>
                      <span
                        className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium text-white"
                        style={{
                          backgroundColor:
                            b.risk_score >= 0.7
                              ? "var(--risk-high)"
                              : "var(--risk-medium)",
                        }}
                      >
                        {formatRiskScore(b.risk_score)}
                      </span>
                    </TableCell>
                    <TableCell className="text-yellow-400 text-xs font-medium">
                      {formatDiscount(b.discount_rate)}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
