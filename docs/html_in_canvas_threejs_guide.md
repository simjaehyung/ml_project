# HTML-in-Canvas + Three.js 제작 가이드

> 2026-05-28 첫 작성. canvas_demo_v3.html 제작 과정에서 정리.
> 기반 레포: github.com/SawyerHood/html-in-canvas-room

---

## 핵심 개념 한 줄 요약

**WebGL 3D 씬 안에 실제 살아있는 HTML DOM을 텍스처로 렌더링한다.**

기존 Canvas는 HTML을 픽셀로 직접 그려야 했고, AI 에이전트도 읽지 못했다.
`texElementImage2D` 하나로 CSS 스타일, 애니메이션, 인터랙션이 살아있는 DOM이
WebGL 텍스처로 올라간다.

---

## 활성화 방법

```
chrome://flags/#canvas-draw-element  →  Enabled  →  Relaunch
```

Chrome Canary 또는 일반 Chrome M146+ 에서 동작.

---

## 핵심 API 2개

### 1. `gl.texElementImage2D` (WebGL2 경로 — 추천)
```javascript
const gl = renderer.getContext(); // Three.js WebGL2 컨텍스트

// WebGL 텍스처 생성
const glTex = gl.createTexture();
gl.bindTexture(gl.TEXTURE_2D, glTex);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);

// DOM 요소 → WebGL 텍스처 (매 프레임 또는 dirty 시)
gl.bindTexture(gl.TEXTURE_2D, glTex);
gl.texElementImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, domElement);
renderer.state.reset(); // Three.js 상태 동기화 필수
```

### 2. `ctx.drawElement` (Canvas 2D 경로 — 폴백용)
```javascript
const offscreen = document.createElement('canvas');
const ctx = offscreen.getContext('2d');
await ctx.drawElement(domElement, 0, 0, width, height);
// 이후 offscreen을 THREE.CanvasTexture로 사용
```

---

## Three.js 연결 패턴 (핵심)

```javascript
// Three.js Texture 객체를 만들되, 내부 WebGL 텍스처를 우리가 직접 관리
const tex = new THREE.Texture();
tex.minFilter = THREE.LinearFilter;
tex.magFilter = THREE.LinearFilter;
tex.generateMipmaps = false;

// Three.js 내부 속성에 직접 주입
const props = renderer.properties.get(tex);
props.__webglTexture = glTex;   // 우리가 만든 WebGL 텍스처
props.__webglInit = true;        // Three.js가 재초기화하지 않도록

// 메시에 적용
const mat = new THREE.MeshBasicMaterial({ map: tex });
const mesh = new THREE.Mesh(geometry, mat);
```

---

## 전체 아키텍처 패턴

```
┌─────────────────────────────────────────────────┐
│  HTML DOM (숨겨진 패널 — position:fixed;left:-9999px)
│    └── 실제 CSS 스타일, 차트, 텍스트, 애니메이션   │
└──────────────────┬──────────────────────────────┘
                   │ gl.texElementImage2D() — 매 프레임
                   ▼
┌─────────────────────────────────────────────────┐
│  WebGL Texture (GPU)                            │
│    renderer.properties.__webglTexture 주입       │
└──────────────────┬──────────────────────────────┘
                   │ THREE.MeshBasicMaterial({ map })
                   ▼
┌─────────────────────────────────────────────────┐
│  Three.js 3D 씬                                 │
│    PlaneGeometry / BoxGeometry 표면에 텍스처 적용  │
│    카메라 lerp 애니메이션으로 공간 이동             │
└─────────────────────────────────────────────────┘
```

---

## 최소 작동 템플릿

```html
<!DOCTYPE html>
<html>
<head>
<style>
  body { margin:0; overflow:hidden; background:#000; }
  /* DOM 패널: 화면 밖에 두되 DOM에는 존재 */
  #my-panel {
    position: fixed; left: -9999px; top: 0;
    width: 512px; height: 384px;
    background: #07101F; color: #fff;
    font-family: Inter, sans-serif; padding: 24px;
  }
</style>
</head>
<body>

<!-- 1. 렌더링 소스가 될 DOM 패널 -->
<div id="my-panel">
  <h1 style="color:#F87171;">취소 위험 87%</h1>
  <p>이 HTML이 3D 씬 안 벽에 붙습니다.</p>
</div>

<script type="importmap">
{ "imports": { "three": "https://cdn.jsdelivr.net/npm/three@0.165.0/build/three.module.js" } }
</script>

<script type="module">
import * as THREE from 'three';

// Three.js 기본 세팅
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);

const scene  = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(60, innerWidth/innerHeight, 0.1, 100);
camera.position.set(0, 0, 3);

// WebGL2 컨텍스트 & API 확인
const gl = renderer.getContext();
const hasApi = typeof gl.texElementImage2D === 'function';
console.log('HTML-in-Canvas:', hasApi ? '✅ 활성화됨' : '❌ 플래그 필요');

// WebGL 텍스처 생성
const glTex = gl.createTexture();
gl.bindTexture(gl.TEXTURE_2D, glTex);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);

// Three.js Texture에 주입
const tex = new THREE.Texture();
tex.minFilter = tex.magFilter = THREE.LinearFilter;
tex.generateMipmaps = false;
Object.assign(renderer.properties.get(tex), {
  __webglTexture: glTex,
  __webglInit: true,
});

// 메시 생성 (비율 4:3 = 512:384)
const mesh = new THREE.Mesh(
  new THREE.PlaneGeometry(4, 3),
  new THREE.MeshBasicMaterial({ map: tex })
);
scene.add(mesh);
scene.add(new THREE.AmbientLight(0xffffff));

// 렌더 루프
const panel = document.getElementById('my-panel');
(function loop() {
  requestAnimationFrame(loop);
  if (hasApi) {
    gl.bindTexture(gl.TEXTURE_2D, glTex);
    gl.texElementImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, panel);
    renderer.state.reset();
  }
  renderer.render(scene, camera);
})();
</script>
</body>
</html>
```

---

## 주의사항

| 항목 | 내용 |
|------|------|
| `renderer.state.reset()` | `texElementImage2D` 후 **반드시** 호출. 안 하면 Three.js 상태 꼬임 |
| DOM 패널 위치 | `display:none` 금지 — 레이아웃 계산이 안 됨. `left:-9999px`으로 숨길 것 |
| 텍스처 비율 | DOM 패널 크기(px)와 PlaneGeometry 비율을 맞출 것 (512:384 = 4:3) |
| `generateMipmaps` | false 필수. DOM 텍스처는 POT(2의 거듭제곱) 아닐 수 있음 |
| 업데이트 빈도 | 정적 콘텐츠면 dirty 플래그로 필요할 때만 업로드. 매 프레임은 GPU 낭비 |
| Chrome 버전 | M146+ (일반 Chrome) 또는 Canary. 플래그 활성화 필수 |

---

## 응용 아이디어

- **3D 호텔 복도** (canvas_demo_v3.html) — 방 뒷벽에 DSS 패널
- **데이터 대시보드 큐브** — 6면 각각 다른 차트
- **발표 슬라이드 3D 공간** — 슬라이드가 3D 오브젝트로 떠있음
- **인터랙티브 포트폴리오** — 3D 방에 프로젝트 패널들
- **실시간 모니터링 벽** — 서버 상태가 3D 공간에 타일로 배열

---

## 참고 레포

- [SawyerHood/html-in-canvas-room](https://github.com/SawyerHood/html-in-canvas-room) — CRT 방 데모 (TypeScript + Three.js + WXT)
- [tomasferrerasdev/try-html-in-canvas](https://github.com/tomasferrerasdev/try-html-in-canvas) — WebGL 셰이더 적용 데모
- [WICG/html-in-canvas](https://github.com/WICG/html-in-canvas) — 공식 스펙 제안
- [remotion-dev/html-in-canvas](https://github.com/remotion-dev/html-in-canvas) — 비디오 렌더링 응용
