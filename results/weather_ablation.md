# Weather Ablation Study — LightGBM

Weather columns found (5): ['precipitation_sum', 'precipitation_hours', 'temperature_2m_max', 'temperature_2m_min', 'wind_speed_10m_max']

| Model | PR-AUC | 95% CI (bootstrap n=200) |
|-------|--------|--------------------------|
| WITH weather | 0.8189 | [0.8128, 0.8245] |
| WITHOUT weather | 0.8166 | [0.8107, 0.8222] |
| Delta | +0.0022 | — |

Top 5 feature importances (gain, WITH weather):
  1. lead_time: 71403.33
  2. country_grouped_PRT: 62519.82
  3. total_of_special_requests: 29284.94
  4. previous_cancellations: 28070.35
  5. market_segment_Online TA: 21036.53

Weather features in top-20: ['temperature_2m_max', 'temperature_2m_min', 'wind_speed_10m_max']