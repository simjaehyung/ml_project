/**
 * PMS TypeScript 타입 — app_pms/pms_schemas.py와 1:1 대응
 */

export type PricingType = "Standard Rate" | "Flexi Rate";
export type BookingStatusPMS = "Confirmed" | "Pending" | "Waitlisted" | "Cancelled";

// ── 관리자 예약 레코드 (에이전트 메타 포함) ──
export interface PMSReservationRecord {
  confirmation_number: string;
  agent_id: string;
  persona_name: string;
  persona_type: string;
  persona_nationality: string;
  hotel: "City Hotel" | "Resort Hotel";
  arrival_date: string;          // YYYY-MM-DD
  departure_date: string;
  nights: number;
  adults: number;
  room_type_assigned: string;
  pricing_type: PricingType;
  rate_per_night: number;
  discount_applied: number | null;
  total_amount: number;
  meal_plan: string;
  status: string;
  dss_booking_id: string | null;
  dss_risk_score: number | null;
  created_at: string;
}

export interface PMSReservationListResponse {
  reservations: PMSReservationRecord[];
  total: number;
}

// ── 실시간 활동 로그 ──
export interface PMSActivityEvent {
  event_id: string;
  timestamp: string;
  agent_id: string;
  persona_name: string;
  persona_type: string;
  action: "thinking" | "booking" | "confirmed" | "error";
  message: string;
  confirmation_number: string | null;
  hotel: string | null;
  pricing_type: PricingType | null;
  discount_pct: number | null;
}

export interface PMSActivityResponse {
  events: PMSActivityEvent[];
  total: number;
}

// ── 통계 ──
export interface PMSStats {
  total_reservations: number;
  flexi_count: number;
  standard_count: number;
  unique_agents: number;
  recent_activity: number;
}

// ── 페르소나 프론트엔드 정의 (personas.py와 동기화) ──
export interface PersonaInfo {
  id: string;
  name: string;
  nationality: string;
  persona_type: string;
  avatar_color: string;
  avatar_initials: string;
  flag: string;
  risk_tendency: "high" | "medium" | "low";
  description: string;
}

export const PERSONAS: PersonaInfo[] = [
  {
    id: "guest-ana",
    name: "Ana Rodrigues",
    nationality: "PRT",
    persona_type: "Business Traveler",
    avatar_color: "#3B82F6",
    avatar_initials: "AR",
    flag: "🇵🇹",
    risk_tendency: "high",
    description: "포르투갈 리스본 출신 비즈니스 여행객. 회의 일정에 따라 예약하며 가끔 취소 발생.",
  },
  {
    id: "guest-james",
    name: "James Mitchell",
    nationality: "GBR",
    persona_type: "Leisure Tourist",
    avatar_color: "#8B5CF6",
    avatar_initials: "JM",
    flag: "🇬🇧",
    risk_tendency: "medium",
    description: "영국 런던 출신 여름 휴가 여행객. 가격에 민감하며 Flexi 요금에 긍정적.",
  },
  {
    id: "guest-marie",
    name: "Marie Dubois",
    nationality: "FRA",
    persona_type: "Family Vacation",
    avatar_color: "#10B981",
    avatar_initials: "MD",
    flag: "🇫🇷",
    risk_tendency: "low",
    description: "프랑스 파리 출신 가족 단위 여행객. 세심하게 계획하고 특별 요청이 많음.",
  },
  {
    id: "guest-thomas",
    name: "Thomas Müller",
    nationality: "DEU",
    persona_type: "Conference",
    avatar_color: "#F59E0B",
    avatar_initials: "TM",
    flag: "🇩🇪",
    risk_tendency: "medium",
    description: "독일 베를린 출신 컨퍼런스 참석자. 일정이 불확실하여 취소 가능성 있음.",
  },
  {
    id: "guest-paulo",
    name: "Paulo Santos",
    nationality: "BRA",
    persona_type: "Solo Traveler",
    avatar_color: "#EF4444",
    avatar_initials: "PS",
    flag: "🇧🇷",
    risk_tendency: "high",
    description: "브라질 상파울루 출신 배낭 여행객. 자주 계획을 바꾸고 취소 이력 있음.",
  },
];

export const PERSONA_BY_ID: Record<string, PersonaInfo> = Object.fromEntries(
  PERSONAS.map((p) => [p.id, p])
);

/** risk_tendency → 색상 */
export function getRiskTendencyColor(tendency: "high" | "medium" | "low"): string {
  if (tendency === "high") return "#FB7185";
  if (tendency === "medium") return "#FBBF24";
  return "#34D399";
}

/** discount_applied → 표시 문자열 */
export function formatDiscount(discount: number | null): string {
  if (!discount) return "—";
  return `-${(discount * 100).toFixed(1)}%`;
}
