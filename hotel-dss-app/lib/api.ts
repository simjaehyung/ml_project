import type {
  BookingAnalysis,
  BookingRequest,
  BookingResponse,
  BookingListItem,
  BookingListResponse,
  BookingStatus,
  DashboardSummary,
  FlexiPreview,
} from "@/types/api";

const BASE_URL = "http://localhost:8001/api/v1";

// ── 에러 처리 헬퍼 ──────────────────────────────────────────────────
async function handleResponse<T>(res: Response): Promise<T> {
  if (res.ok) {
    return res.json() as Promise<T>;
  }
  if (res.status === 422) {
    const body = await res.json().catch(() => null);
    // FastAPI 422: body.detail는 배열 또는 문자열일 수 있음
    const detail = body?.detail;
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0];
      const field = first?.loc?.slice(1).join(".") ?? "unknown";
      const msg = first?.msg ?? "Validation error";
      throw new Error(`[${field}] ${msg}`);
    }
    throw new Error(typeof detail === "string" ? detail : "Validation error (422)");
  }
  throw new Error(`HTTP ${res.status}: ${res.statusText}`);
}

// ── API 함수 ──────────────────────────────────────────────────────

/** 신규 예약 생성 + 위험도 예측 */
export async function createBooking(data: BookingRequest): Promise<BookingResponse> {
  const res = await fetch(`${BASE_URL}/bookings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<BookingResponse>(res);
}

/** 예약 목록 조회 (상태·최소 위험도 필터 선택) */
export async function listBookings(params?: {
  status?: BookingStatus;
  min_risk?: number;
}): Promise<BookingListResponse> {
  const url = new URL(`${BASE_URL}/bookings`);
  if (params?.status) url.searchParams.set("status", params.status);
  if (params?.min_risk !== undefined)
    url.searchParams.set("min_risk", String(params.min_risk));
  const res = await fetch(url.toString());
  return handleResponse<BookingListResponse>(res);
}

/** 단일 예약 조회 */
export async function getBooking(id: string): Promise<BookingListItem> {
  const res = await fetch(`${BASE_URL}/bookings/${id}`);
  return handleResponse<BookingListItem>(res);
}

/** 예약 전체 분석 — SHAP 상위 10개 요인 + Flexi 근거 (매니저 상세 페이지용) */
export async function getBookingAnalysis(id: string): Promise<BookingAnalysis> {
  const res = await fetch(`${BASE_URL}/bookings/${id}/analysis`);
  return handleResponse<BookingAnalysis>(res);
}

/** 대시보드 KPI 요약 */
export async function getDashboardSummary(): Promise<DashboardSummary> {
  const res = await fetch(`${BASE_URL}/dashboard/summary`);
  return handleResponse<DashboardSummary>(res);
}

/** Flexi 임계값 미리보기 */
export async function getFlexiPreview(threshold: number): Promise<FlexiPreview> {
  const url = new URL(`${BASE_URL}/flexi/preview`);
  url.searchParams.set("threshold", String(threshold));
  const res = await fetch(url.toString());
  return handleResponse<FlexiPreview>(res);
}
