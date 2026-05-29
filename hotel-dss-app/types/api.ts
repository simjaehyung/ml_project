/**
 * Hotel DSS — TypeScript 타입 정의 (이고은 전용)
 *
 * api/schemas.py의 Pydantic 스키마와 1:1 대응.
 *
 * 규칙:
 *  - 필드명은 Python snake_case 그대로 사용 (camelCase 변환 금지)
 *  - enum 문자열은 schemas.py와 완전히 동일해야 한다
 *  - 백엔드가 스키마를 바꾸면 이 파일도 동시에 바꾼다
 */


// ══════════════════════════════════════════════════════════════════
// SECTION 1: 공유 enum 상수
// ══════════════════════════════════════════════════════════════════

export type HotelType = "City Hotel" | "Resort Hotel";

export type ChannelType = "Direct" | "Corporate" | "TA/TO" | "GDS" | "Undefined";

export type MarketSegmentType =
  | "Direct"
  | "Corporate"
  | "Online TA"
  | "Offline TA/TO"
  | "Groups"
  | "Complementary"
  | "Aviation";

export type RoomType = "A" | "B" | "C" | "D" | "E" | "F" | "G" | "H" | "L";

export type MealType = "BB" | "HB" | "FB" | "SC" | "Undefined";

export type CustomerType = "Transient" | "Contract" | "Transient-Party" | "Group";

export type BookingStatus = "confirmed" | "high-risk" | "flexi-routed";

export type ConfidenceLevel = "HIGH" | "MEDIUM" | "LOW";


// ══════════════════════════════════════════════════════════════════
// SECTION 2: App 1 폼 → FastAPI (Request)
// ══════════════════════════════════════════════════════════════════

export interface BookingRequest {
  // 호텔
  hotel: HotelType;

  // 날짜 (ISO 8601 문자열: "YYYY-MM-DD")
  arrival_date: string;
  departure_date: string;

  // 인원
  adults: number;          // 1~55
  children: number;        // 0~10, 기본 0
  babies: number;          // 0~10, 기본 0

  // 채널
  distribution_channel: ChannelType;
  market_segment: MarketSegmentType;

  // 방·식사
  reserved_room_type: RoomType;
  meal: MealType;

  // 고객
  country: string;             // ISO 3166-1 alpha-3, 3자리 대문자. 예: "GBR"
  is_repeated_guest: 0 | 1;   // 기본 0
  previous_cancellations: number;   // 0~26, 기본 0
  booking_changes: number;          // 0~21, 기본 0

  // 조건
  customer_type: CustomerType;
  adr: number;                              // 0 이상 실수
  required_car_parking_spaces: number;     // 0~8, 기본 0
  total_of_special_requests: number;       // 0~5, 기본 0
}


// ══════════════════════════════════════════════════════════════════
// SECTION 3: FastAPI → App 1/2 (Response)
// ══════════════════════════════════════════════════════════════════

export interface RiskFactor {
  feature: string;      // 내부 피처명. 예: "lead_time"
  label: string;        // 화면 표시용. 예: "리드타임 92일 (평균보다 41일 길다)"
  shap_value: number;   // 양수 = 위험 증가 기여
}

export interface BookingResponse {
  booking_id: string;                     // 예: "BK-3F9A1C"
  risk_score: number;                     // 0~1
  flexi_recommended: boolean;
  discount_rate: number | null;           // flexi_recommended 일 때만 값 존재 (0.05~0.18)
  top_risk_factors: RiskFactor[];         // 항상 3개
  confidence: ConfidenceLevel;
  status: BookingStatus;
  created_at: string;                     // ISO 8601 datetime 문자열
}


// ══════════════════════════════════════════════════════════════════
// SECTION 4: App 2 대시보드 목록
// ══════════════════════════════════════════════════════════════════

export interface BookingListItem {
  booking_id: string;
  hotel: HotelType;
  country: string;
  arrival_date: string;         // "YYYY-MM-DD"
  nights: number;
  adults: number;
  risk_score: number;
  flexi_recommended: boolean;
  discount_rate: number | null;
  status: BookingStatus;
  created_at: string;
}

export interface BookingListResponse {
  bookings: BookingListItem[];
  total: number;
}


// ══════════════════════════════════════════════════════════════════
// SECTION 4b: 예약 전체 분석 (매니저 상세 페이지용)
// ══════════════════════════════════════════════════════════════════

export interface BookingAnalysis {
  booking_id: string;
  risk_score: number;
  flexi_recommended: boolean;
  discount_rate: number | null;
  confidence: ConfidenceLevel;
  top_risk_factors: RiskFactor[];         // SHAP 상위 10개
  flexi_rationale: string;                // Flexi 권장 근거 텍스트
  estimated_loss_if_cancel: number;       // 취소 시 예상 손실 (통화 단위)
  estimated_flexi_discount: number;       // Flexi 할인 적용 비용 (통화 단위)
}


// ══════════════════════════════════════════════════════════════════
// SECTION 5: 대시보드 KPI 요약
// ══════════════════════════════════════════════════════════════════

export interface DashboardSummary {
  total_bookings: number;        // KPI 카드 1
  high_risk_count: number;       // KPI 카드 2
  flexi_routed_count: number;    // KPI 카드 3
  avg_risk_score: number;        // KPI 카드 4
  current_threshold: number;     // 현재 Flexi 임계값
  last_updated: string;          // ISO 8601 datetime
}


// ══════════════════════════════════════════════════════════════════
// SECTION 6: Flexi 임계값 미리보기
// ══════════════════════════════════════════════════════════════════

export interface FlexiPreview {
  threshold: number;              // 0.50~0.85
  estimated_pool_size: number;
  estimated_walk_rate: number;    // 0~1
  baseline_walk_rate: number;
  walk_rate_improvement: number;
}


// ══════════════════════════════════════════════════════════════════
// SECTION 7: LLM 에이전트 전용
// ══════════════════════════════════════════════════════════════════

export interface LLMBookingRequest extends BookingRequest {
  agent_id: string;
  persona: string;
}

export interface LLMDashboardState {
  total_bookings: number;
  high_risk_count: number;
  flexi_routed_count: number;
  recent_bookings: BookingListItem[];    // 최근 5건
  current_threshold: number;
}


// ══════════════════════════════════════════════════════════════════
// SECTION 8: 에러 응답
// ══════════════════════════════════════════════════════════════════

export interface ErrorResponse {
  code: string;
  message: string;
  field?: string;
}


// ══════════════════════════════════════════════════════════════════
// SECTION 9: UI 유틸 (이고은 전용 헬퍼)
// ══════════════════════════════════════════════════════════════════

/** risk_score → 뱃지 색상 매핑 */
export function getRiskBadgeVariant(
  score: number
): "destructive" | "warning" | "success" {
  if (score >= 0.7) return "destructive";  // 빨간 뱃지
  if (score >= 0.4) return "warning";      // 노란 뱃지
  return "success";                         // 초록 뱃지
}

/** risk_score → 퍼센트 문자열 */
export function formatRiskScore(score: number): string {
  return `${(score * 100).toFixed(1)}%`;
}

/** discount_rate → 퍼센트 문자열 */
export function formatDiscount(rate: number | null): string {
  if (rate === null) return "—";
  return `${(rate * 100).toFixed(1)}%`;
}

/** ISO alpha-3 → 국기 이모지 (주요 국가) */
export const COUNTRY_FLAGS: Record<string, string> = {
  PRT: "🇵🇹", GBR: "🇬🇧", FRA: "🇫🇷", ESP: "🇪🇸",
  DEU: "🇩🇪", IRL: "🇮🇪", BEL: "🇧🇪", BRA: "🇧🇷",
  NLD: "🇳🇱", ITA: "🇮🇹", USA: "🇺🇸", CHN: "🇨🇳",
};
export function getCountryFlag(iso3: string): string {
  return COUNTRY_FLAGS[iso3] ?? "🌐";
}
