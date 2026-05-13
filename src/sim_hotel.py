"""
sim_hotel.py
호텔 환경 — Flexi 라우팅 로직 + 시나리오별 RevPAR / walk_rate 계산

RevPAR 모델:
  - 기준선: Σ ADR × (1 - cancel_prob)  / 총 예약 수
  - Flexi 적용: 수락자는 할인 ADR × 감소된 취소 확률로 계산
  - Walk rate: Flexi 수락자의 실제 도착 수 분포로 통계 추정 (정규 근사)
"""

import numpy as np
import pandas as pd
from scipy.stats import norm

FLEXI_CANCEL_REDUCTION = 0.50   # Flexi 수락 시 취소 확률 감소 비율 (할인 효과 추정)
OVERBOOKING_BUFFER     = 0.05   # 호텔 오버부킹 허용 버퍼 5%


def simulate_threshold(df: pd.DataFrame, threshold: float) -> dict:
    """
    df 컬럼 필수: cancel_prob, adr, discount, decision
    threshold: 이 값 이상이면 Flexi 오퍼를 제시한 것으로 간주
    """
    standard  = df[df["cancel_prob"] < threshold]
    offered   = df[df["cancel_prob"] >= threshold]

    accepted  = offered[offered["decision"] == "ACCEPT_FLEXI"]
    declined  = offered[offered["decision"] == "DECLINE_FLEXI"]
    cancelled = offered[offered["decision"] == "CANCEL"]

    # ── RevPAR 계산 ──────────────────────────────────────────────────────────
    # 기준선: Flexi 없을 때 예상 수익 (전체 예약)
    baseline_rev = (df["adr"] * (1 - df["cancel_prob"])).sum()

    rev_standard = (standard["adr"] * (1 - standard["cancel_prob"])).sum()

    # 수락자: 할인 ADR × 낮아진 취소 확률
    reduced_cancel = accepted["cancel_prob"] * FLEXI_CANCEL_REDUCTION
    rev_accepted   = (accepted["adr"] * (1 - accepted["discount"] / 100)
                      * (1 - reduced_cancel)).sum()

    rev_declined  = (declined["adr"]  * (1 - declined["cancel_prob"])).sum()
    rev_cancelled = 0.0   # CANCEL 결정 → 수익 없음

    total_rev         = rev_standard + rev_accepted + rev_declined + rev_cancelled
    revpar_uplift_pct = ((total_rev - baseline_rev) / baseline_rev * 100
                         if baseline_rev > 0 else 0.0)

    # ── Walk rate (정규 근사) ─────────────────────────────────────────────────
    # Flexi 수락자만 대상 — 각자 독립 베르누이(show_prob)
    if len(accepted) == 0:
        walk_rate = 0.0
    else:
        p_show          = 1 - accepted["cancel_prob"] * FLEXI_CANCEL_REDUCTION
        expected        = p_show.sum()
        variance        = (p_show * (1 - p_show)).sum()
        std             = float(np.sqrt(max(variance, 1e-9)))
        capacity        = expected * (1 + OVERBOOKING_BUFFER)
        # walk = P(실제 도착 > 수용 가능 인원)
        walk_rate       = float(1 - norm.cdf(capacity, loc=expected, scale=std))

    n_offered = len(offered)
    return {
        "threshold":         threshold,
        "n_total":           len(df),
        "n_standard":        len(standard),
        "n_offered":         n_offered,
        "n_accepted":        len(accepted),
        "n_declined":        len(declined),
        "n_cancelled":       len(cancelled),
        "accept_rate":       round(len(accepted) / n_offered, 4) if n_offered > 0 else 0.0,
        "cancel_rate_flexi": round(len(cancelled) / n_offered, 4) if n_offered > 0 else 0.0,
        "revpar_uplift_pct": round(float(revpar_uplift_pct), 3),
        "walk_rate_pct":     round(walk_rate * 100, 4),
        "baseline_rev":      round(float(baseline_rev), 1),
        "flexi_rev":         round(float(total_rev), 1),
        "rev_gain":          round(float(total_rev - baseline_rev), 1),
    }


def sweep_thresholds(df: pd.DataFrame, thresholds: list) -> pd.DataFrame:
    rows = [simulate_threshold(df, t) for t in thresholds]
    return pd.DataFrame(rows)


def find_optimal_threshold(sweep_df: pd.DataFrame, max_walk_rate_pct: float = 2.0) -> dict | None:
    safe = sweep_df[sweep_df["walk_rate_pct"] <= max_walk_rate_pct]
    if len(safe) == 0:
        return None
    best_idx = safe["revpar_uplift_pct"].idxmax()
    return safe.loc[best_idx].to_dict()
