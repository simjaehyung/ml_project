# 학교 서버 Claude 에이전트 — 실행 지시문

> 이 파일은 학교 서버(curie, RTX A5000 × 4)의 Claude 에이전트에게 붙여넣을 프롬프트다.
> 심재형이 작성. 에이전트는 이 지시를 따라 서버 상태를 스스로 판단하고 시뮬레이션을 실행한다.

---

## 아래 내용을 학교 서버 Claude 에이전트에게 그대로 붙여넣기

---

너는 지금 호텔 오버부킹 Walk 보상 협상 시뮬레이션 프로젝트를 진행 중인 서버 에이전트야.
목표는 `src/sim_overbooking.py`를 실행해서 시뮬레이션 결과를 GitHub에 올리는 것이다.

**서버 환경:**
- 호스트: curie (Ubuntu 24.04)
- GPU: RTX A5000 × 4 (VRAM 24GB × 4)
- Python: 3.11.5
- 프로젝트 경로: ~/ml_project (또는 git clone된 위치)
- vLLM 대상 모델: Qwen/Qwen2.5-14B-Instruct (GPU 0,1 사용, tensor-parallel=2)

---

### STEP 1 — 최신 코드 가져오기

```bash
cd ~/ml_project
git pull origin main
```

오류 나면 stash 후 pull:
```bash
git stash && git pull origin main && git stash pop
```

---

### STEP 2 — 서버 상태 점검

```bash
python src/sim_overbooking.py --check
```

출력을 읽고 아래 분기를 따라라:

**케이스 A — vLLM 미실행 + GPU 여유 2장 이상**
```bash
mkdir -p logs
nohup bash start_vllm.sh > logs/vllm.log 2>&1 &
echo "vLLM 시작됨. 90초 대기..."
sleep 90
python src/sim_overbooking.py --check
```
--check 재실행 후 vLLM 정상이면 STEP 3으로.

**케이스 B — vLLM 실행 중 + GPU 여유 2장 이상**
바로 STEP 3으로.

**케이스 C — GPU 모두 사용 중 (다른 팀원 사용)**
```bash
# 30분 후 재시도
sleep 1800
python src/sim_overbooking.py --check
```
상황 개선 안 되면 Anthropic API 폴백(STEP 3-B) 사용.

**케이스 D — vLLM 실행 중이지만 GPU 1장뿐**
STEP 3-B (Anthropic API 폴백) 사용.

---

### STEP 3-A — 파일럿 실행 (vLLM, 권장)

GPU 여유 2장일 때 여유 GPU 인덱스를 확인해서 실행:

```bash
# --check 출력에서 "권장 GPU: X,Y" 확인 후
# workers는 GPU 여유에 따라 조정 (여유 2장 → workers 8)
python src/sim_overbooking.py --pilot --model vllm --workers 8
```

파일럿 출력에서 확인할 것:
1. `JSON 파싱 성공률 (R1)` >= 95% 인지
2. 아키타입 A와 D의 수락률이 서로 다른지 (완전히 같으면 문제)
3. 에러 없이 60회 완료됐는지

파일럿 [OK] 면 → 전체 실행으로.
파일럿 [NG] (파싱 실패 많거나 에러) 면 → 이 파일 하단 트러블슈팅 참고.

---

### STEP 3-B — Anthropic API 폴백

vLLM 사용 불가하거나 파일럿 실패 시 사용. `ANTHROPIC_API_KEY` 환경변수 필요.

```bash
# API 키 확인
echo $ANTHROPIC_API_KEY

# 파일럿
python src/sim_overbooking.py --pilot --model anthropic --workers 4
# 기본값: claude-sonnet-4-6 (GPT-4급, Homo Silicus 논문 조건과 동급)
# Haiku로 낮추려면: --model-name claude-haiku-4-5-20251001

# 전체
python src/sim_overbooking.py --model anthropic --workers 4
```

---

### STEP 4 — 전체 1,000회 실행

```bash
# vLLM 사용 시
python src/sim_overbooking.py --model vllm --workers 8 \
    --out results/walk_sim_results.jsonl

# 진행 상황은 tqdm 프로그레스바로 확인
# 예상 소요: ~20~40분 (vLLM 기준)
```

---

### STEP 5 — 결과 확인 및 GitHub 업로드

```bash
# 요약 CSV 위치 확인
ls -lh results/walk_sim_results_summary.csv

# 내용 확인 (아키타입별 수락률)
python -c "
import pandas as pd
df = pd.read_csv('results/walk_sim_results_summary.csv')
print(df.groupby(['archetype','archetype_label'])['accept_rate'].mean().to_string())
"

# Claim 2 방향성 체크:
# Family(C) 수락률 < Budget OTA(D) 수락률 이어야 한다
# (가족이 더 높은 보상을 요구하므로 낮은 오퍼에서 수락률이 낮음)
```

결과가 합리적이면 GitHub push:

```bash
git add results/walk_sim_results_summary.csv
git commit -m "feat: Walk 협상 시뮬레이션 결과 추가 (1000회)"
git push origin main
```

---

### 트러블슈팅

**vLLM OOM (Out of Memory)**
```bash
# start_vllm.sh에서 --gpu-memory-utilization 0.88 → 0.80으로 낮추기
sed -i 's/0.88/0.80/' start_vllm.sh
bash start_vllm.sh
```

**JSON 파싱 실패율 > 10%**
```bash
# JSONL에서 파싱 실패 샘플 확인
python -c "
import json
with open('results/walk_sim_results.jsonl') as f:
    rows = [json.loads(l) for l in f if l.strip()]
failed = [r for r in rows if not r.get('r1_parse_ok', True)]
print(f'파싱 실패: {len(failed)}건')
if failed:
    print('샘플:', failed[0].get('r1_raw', '')[:300])
"
```
파싱 실패가 많으면 심재형에게 보고 (Anthropic API 전환 검토).

**vLLM 서버 로그 확인**
```bash
tail -50 logs/vllm.log
```

**이미 실행 중인 vLLM 프로세스 확인**
```bash
ps aux | grep vllm
```

---

### 완료 보고 형식

실행 완료 후 심재형에게 아래 형식으로 보고:

```
[완료] Walk 시뮬레이션 결과

실행 환경: [vllm / anthropic]
총 협상: [N]회
소요 시간: [N]분

아키타입별 평균 수락률:
  A (Business Solo):  XX%
  B (Leisure Couple): XX%
  C (Family):         XX%
  D (Budget OTA):     XX%
  E (Group):          XX%

Claim 2 방향성: [OK - C < D 확인됨 / NG - 재검토 필요]
JSON 파싱 성공률: XX%

GitHub: results/walk_sim_results_summary.csv push 완료
```
