#!/bin/bash
# sim_setup.sh
# 학교 서버 (Ubuntu 24.04, RTX A5000 × 4, Python 3.11.5) 환경 셋업
# 실행: bash src/sim_setup.sh

set -e
echo "=================================================="
echo " Flexi LLM 시뮬레이션 서버 셋업"
echo " curie | Qwen2.5-14B-Instruct | 2x A5000"
echo "=================================================="

# ── 1. GPU 상태 확인 ──────────────────────────────────────────────────────────
echo ""
echo "▶ GPU 상태 확인..."
nvidia-smi --query-gpu=index,name,memory.used,memory.free --format=csv,noheader
echo ""
echo "  GPU 2장 (GPU 0, 1)이 비어있으면 계속 진행."
echo "  다른 사람이 쓰고 있으면 먼저 확인하세요 (다들 알림 주기)."
read -p "  계속하시겠습니까? [y/N] " confirm
[[ "$confirm" != "y" && "$confirm" != "Y" ]] && exit 0

# ── 2. 패키지 설치 ────────────────────────────────────────────────────────────
echo ""
echo "▶ 패키지 설치..."
pip install --quiet --upgrade pip

# vLLM (CUDA 13.0 / Ampere A5000 호환)
pip install --quiet vllm

# openai client (vLLM OpenAI-compatible API 용)
pip install --quiet "openai>=1.0"

# 시뮬레이션 의존 패키지
pip install --quiet scipy tqdm

echo "  설치 완료."

# ── 3. 모델 다운로드 확인 ─────────────────────────────────────────────────────
MODEL_DIR="$HOME/.cache/huggingface/hub"
MODEL_NAME="Qwen/Qwen2.5-14B-Instruct"

echo ""
echo "▶ 모델 캐시 확인: $MODEL_NAME"
if python -c "from huggingface_hub import snapshot_download; snapshot_download('$MODEL_NAME', local_files_only=True)" 2>/dev/null; then
    echo "  캐시 있음 — 다운로드 생략."
else
    echo "  다운로드 시작 (약 28GB, 수분 소요)..."
    python -c "
from huggingface_hub import snapshot_download
snapshot_download('$MODEL_NAME', ignore_patterns=['*.pt'])
print('  다운로드 완료.')
"
fi

# ── 4. vLLM 서버 시작 스크립트 생성 ──────────────────────────────────────────
cat > start_vllm.sh << 'EOF'
#!/bin/bash
# start_vllm.sh — vLLM 서버 시작 (GPU 0,1 사용, BF16, 포트 8000)
# 백그라운드 실행: nohup bash start_vllm.sh > logs/vllm.log 2>&1 &

mkdir -p logs

CUDA_VISIBLE_DEVICES=0,1 python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-14B-Instruct \
    --tensor-parallel-size 2 \
    --dtype bfloat16 \
    --port 8000 \
    --max-model-len 2048 \
    --gpu-memory-utilization 0.88 \
    2>&1 | tee logs/vllm.log
EOF
chmod +x start_vllm.sh
echo ""
echo "▶ start_vllm.sh 생성 완료."

# ── 5. 서버 상태 확인 헬퍼 ───────────────────────────────────────────────────
cat > check_vllm.sh << 'EOF'
#!/bin/bash
# check_vllm.sh — vLLM 서버 응답 확인
echo "▶ vLLM 서버 상태 확인 (localhost:8000)..."
curl -s http://localhost:8000/health && echo "  서버 정상 작동" || echo "  서버 미응답 — start_vllm.sh 실행 여부 확인"
echo ""
echo "▶ 모델 목록:"
curl -s http://localhost:8000/v1/models | python -m json.tool 2>/dev/null || echo "  응답 없음"
EOF
chmod +x check_vllm.sh
echo "▶ check_vllm.sh 생성 완료."

# ── 6. 실행 순서 안내 ─────────────────────────────────────────────────────────
echo ""
echo "=================================================="
echo " 셋업 완료. 실행 순서:"
echo ""
echo " 1. vLLM 서버 시작 (별도 터미널 또는 tmux):"
echo "    nohup bash start_vllm.sh > logs/vllm.log 2>&1 &"
echo ""
echo " 2. 서버 뜰 때까지 대기 (약 30~60초):"
echo "    bash check_vllm.sh"
echo ""
echo " 3. dry-run으로 파이프라인 검증:"
echo "    python src/sim_run.py --dry-run --n 50"
echo ""
echo " 4. 실제 시뮬레이션 실행 (500건, ~15분):"
echo "    python src/sim_run.py --n 500 --workers 16"
echo ""
echo " 5. 결과 분석 + 시각화:"
echo "    python src/sim_analyze.py"
echo ""
echo " 산출물: results/sim_threshold_sweep.png"
echo "         results/sim_acceptance_breakdown.png"
echo "         results/sim_prob_vs_acceptance.png"
echo "         results/sim_sweep_results.csv"
echo "=================================================="
