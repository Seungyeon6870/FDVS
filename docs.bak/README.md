# 프로젝트 페이지

논문 *Video Stabilization Robust to Large Foreground Motion via Adaptive Hybrid Motion Estimation*
의 프로젝트 페이지. 빌드 도구 없이 정적 HTML/CSS/JS로만 동작한다.

```
projectpage/
├── index.html              내용 전체 (제목·저자·Abstract·Method·Related work·BibTeX)
├── prepare_assets.py       원본 영상 → 웹용 side-by-side mp4 + 썸네일 + data.js 생성
└── static/
    ├── css/style.css
    ├── js/main.js          플레이어·비교 방법 선택 로직 (수정 불필요)
    ├── js/data.js          prepare_assets.py 가 생성 — 직접 수정하지 말 것
    ├── images/pipeline.png figures/fig1_pipeline.png 복사본
    └── videos/             {method}_{n}.mp4 와 thumbs/{n}.jpg
```

## 직접 채워야 하는 것

`index.html` 에서 `EDIT:` 주석이 붙은 두 곳.

1. **버튼 링크** — `data-link="arxiv" | "code" | "dataset"` 세 개의 `href="#"` 를 실제 주소로 교체.
2. **BibTeX** — `#bibtex-content` 안의 내용을 게재 확정 후 갱신.

저자 이름의 `href="#"` 도 개인 홈페이지가 있으면 바꿔 넣으면 된다.

## 영상 다시 만들기

```bash
python prepare_assets.py                        # 기본 12편, 방법 5종
python prepare_assets.py --scenes 34 62 10      # 장면 교체
python prepare_assets.py --duration 8 --crf 34  # 용량 줄이기
python prepare_assets.py --force                # 기존 파일 덮어쓰기
```

좌우를 **하나의 파일로 합쳐서** 인코딩하므로 재생 중 두 화면이 어긋나지 않는다.
장면 목록·비교 방법·원본 경로는 `prepare_assets.py` 상단 상수에서 바꾼다.
원본 경로는 `DATASET_ROOT`, `MASKME_ROOT` 환경 변수로도 덮어쓸 수 있다.

기본 장면 12편은 제안 방법의 BIFMAE 개선폭이 큰 순서로 골랐다
(34, 62, 64, 10, 21, 27, 6, 35, 30, 49, 51, 7).

## 확인

```bash
python serve.py            # http://<서버주소>:8777
python serve.py --port 9000 --bind 127.0.0.1
```

`serve.py` 는 `python -m http.server` 와 같지만 `Cache-Control: no-store` 를 붙이고
조건부 요청을 무시한다. 그림이나 영상을 다시 만들어도 브라우저가 옛 파일을 보여주지 않는다.

`file://` 로 열면 `data.js` 와 영상이 CORS 로 막히므로 반드시 서버로 띄울 것.

원격 머신에서 돌린다면 SSH 포트 포워딩이 안전하다.

```bash
ssh -p <포트> -L 8777:localhost:8777 <사용자>@<서버주소>
```

## 배포

`projectpage/` 를 통째로 GitHub Pages 저장소 루트에 올리면 된다.
현재 `static/videos/` 가 약 64 MB 이므로, 저장소 용량이 부담되면
`--duration` 을 줄이거나 `--crf` 를 높여 다시 생성한다.
