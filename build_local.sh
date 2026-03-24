set -e  # 오류 발생 시 즉시 중단

echo ""
echo "╔══════════════════════════════════════╗"
echo "║     청력검사 — 로컬 빌드 테스트      ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ── 1. 이전 빌드 정리 ─────────────────────────────────────────────
echo "▶ 이전 빌드 정리 중..."
rm -rf dist/청력검사 dist/청력검사.app build/ 청력검사.spec 2>/dev/null || true

# ── 2. PyInstaller 빌드 (GitHub Actions와 동일한 옵션) ────────────
echo "▶ PyInstaller 빌드 시작..."
pyinstaller --onefile --windowed \
  --name "청력검사" \
  --hidden-import=numpy \
  --hidden-import=sounddevice \
  --hidden-import=matplotlib \
  main.py

# ── 3. 빌드 결과 확인 ─────────────────────────────────────────────
echo ""
if [ -f "dist/청력검사" ]; then
  SIZE=$(du -sh dist/청력검사 | cut -f1)
  echo "✅ 빌드 성공! (크기: $SIZE)"
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "   실행파일 위치: dist/청력검사"
  echo ""
  echo "   지금 바로 테스트:  ./dist/청력검사 --demo"
  echo "   전체 검사 테스트:  ./dist/청력검사"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
else
  echo "❌ 빌드 실패 — dist/청력검사 파일이 없습니다."
  exit 1
fi