import type {
  PMSReservationListResponse,
  PMSActivityResponse,
  PMSStats,
} from "@/types/pms";

const PMS_BASE = "http://localhost:3001";

async function handleResponse<T>(res: Response): Promise<T> {
  if (res.ok) return res.json() as Promise<T>;
  throw new Error(`PMS API ${res.status}: ${res.statusText}`);
}

/** 전체 예약 목록 (에이전트 메타 포함) */
export async function getPMSReservations(): Promise<PMSReservationListResponse> {
  const res = await fetch(`${PMS_BASE}/admin/reservations`);
  return handleResponse<PMSReservationListResponse>(res);
}

/** 실시간 활동 로그 */
export async function getPMSActivity(limit = 50): Promise<PMSActivityResponse> {
  const res = await fetch(`${PMS_BASE}/admin/activity?limit=${limit}`);
  return handleResponse<PMSActivityResponse>(res);
}

/** 간단 통계 */
export async function getPMSStats(): Promise<PMSStats> {
  const res = await fetch(`${PMS_BASE}/admin/stats`);
  return handleResponse<PMSStats>(res);
}
