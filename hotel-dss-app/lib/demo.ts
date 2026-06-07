// 발표 데모 'as-of' 기준일 — data/demo_snapshot.json 의 as_of 와 동일하게 유지.
// 백엔드 스냅샷이 테스트셋(2017) 예약이라, 화면의 상대 날짜(리드타임·시간필터)는
// '지금(Date.now)'이 아니라 이 기준일을 기준으로 계산해야 일관된다.
export const DEMO_AS_OF = new Date("2017-06-01T00:00:00");
export const DEMO_AS_OF_LABEL = "2017-06-01";

const DAY = 86400000;

/** 예약 lead time (예약일→도착일, days). created_at 있으면 실제 lead, 없으면 as-of 기준. */
export function leadDays(b: { arrival_date: string; created_at?: string }): number {
  const arr = new Date(b.arrival_date).getTime();
  const base = b.created_at ? new Date(b.created_at).getTime() : DEMO_AS_OF.getTime();
  return Math.max(0, Math.round((arr - base) / DAY));
}

/** as-of 기준 도착까지 남은 일수 (시간 필터/우선순위용). */
export function daysUntilArrival(arrival_date: string): number {
  return Math.ceil((new Date(arrival_date).getTime() - DEMO_AS_OF.getTime()) / DAY);
}
