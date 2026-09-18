#!/usr/bin/env python3
"""프로젝트 페이지용 웹 자산을 생성한다.

각 (비교 방법, 장면) 조합에 대해 `비교 방법 | 제안 방법`을 좌우로 이어 붙인
side-by-side 영상을 만들고, 장면별 썸네일과 페이지가 읽는 `static/js/data.js`를
함께 출력한다. 좌우를 한 파일로 합치기 때문에 재생 중 두 영상이 어긋나지 않는다.

    python prepare_assets.py                       # 기본 장면으로 전체 생성
    python prepare_assets.py --scenes 34 62 10     # 장면 지정
    python prepare_assets.py --duration 8 --crf 32 # 용량 줄이기

원본 데이터 경로는 환경 변수로 바꿀 수 있다.
    DATASET_ROOT  (기본 /home/cvlab/ME/dataset)
    MASKME_ROOT   (기본 이 저장소의 루트)
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(os.environ.get("MASKME_ROOT", PAGE_DIR.parent))
DATASET_ROOT = Path(os.environ.get("DATASET_ROOT", "/home/cvlab/ME/dataset"))

VIDEO_DIR = PAGE_DIR / "static" / "videos"
THUMB_DIR = VIDEO_DIR / "thumbs"
IMAGE_DIR = PAGE_DIR / "static" / "images"
DATA_JS = PAGE_DIR / "static" / "js" / "data.js"

# 제안 방법(오른쪽 화면)
OURS_TEMPLATE = REPO_ROOT / "outputs" / "Adaptve+newQP_dataset_ours" / "H264" / "{n}.mp4"
OURS_LABEL = "Ours"

# 비교 방법(왼쪽 화면). 순서가 페이지의 버튼 순서가 된다.
METHODS = [
    ("original", "Unstable Video", DATASET_ROOT / "H264" / "{n}.mp4"),
    ("bundled", "Bundled Camera Paths", DATASET_ROOT / "outputs" / "Bundled" / "{n}.mp4"),
    ("difrint", "DIFRINT", DATASET_ROOT / "outputs" / "DIFRINT" / "{n}.mp4"),
    ("dut", "DUT", DATASET_ROOT / "outputs" / "DUT" / "{n}.mp4"),
    ("gfn", "GlobalFlowNet-Affine", DATASET_ROOT / "outputs" / "GFN_05" / "{n}.avi"),
]

# 상단 티저에서 쓰는 비교 대상
TEASER_METHOD = "original"

# 제안 방법의 BIFMAE 개선폭이 큰 순서로 고른 기본 장면
DEFAULT_SCENES = ["34", "62", "64", "10", "21", "27", "6", "35", "30", "49", "51", "7"]

# 논문 Fig.1 (파이프라인 개요)
PIPELINE_FIGURE = REPO_ROOT / "figures" / "fig1_pipeline_v2.png"
PIPELINE_WIDTH = 2400  # 원본이 4088px라 웹용으로 줄여 쓴다


def run(cmd):
    """ffmpeg 명령을 실행하고 성공 여부를 돌려준다."""
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if result.returncode != 0:
        sys.stderr.write(result.stderr.decode("utf-8", "replace")[-800:] + "\n")
        return False
    return True


def compose(left_path, right_path, out_path, args):
    """좌우 영상을 한 화면으로 이어 붙여 웹용 mp4로 인코딩한다."""
    w, h = args.width, args.height
    scale = (
        "scale={w}:{h}:force_original_aspect_ratio=decrease,"
        "pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps={fps}"
    ).format(w=w, h=h, fps=args.fps)

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-ss", str(args.start), "-t", str(args.duration), "-i", str(left_path),
        "-ss", str(args.start), "-t", str(args.duration), "-i", str(right_path),
        "-filter_complex",
        "[0:v]{s}[l];[1:v]{s}[r];[l][r]hstack=inputs=2[v]".format(s=scale),
        "-map", "[v]", "-an",
        "-c:v", "libx264", "-crf", str(args.crf), "-preset", args.preset,
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(out_path),
    ]
    return run(cmd)


def make_thumbnail(src_path, out_path, args):
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-ss", str(args.start + args.duration / 2), "-i", str(src_path),
        "-frames:v", "1", "-vf", "scale=320:-2", "-q:v", "4",
        str(out_path),
    ]
    return run(cmd)


def build_jobs(scenes, args):
    """생성해야 할 (설명, 함수) 목록과 매니페스트 뼈대를 만든다."""
    jobs = []
    manifest = []

    for scene in scenes:
        ours = Path(str(OURS_TEMPLATE).format(n=scene))
        if not ours.exists():
            print("  건너뜀: 장면 {} — 제안 방법 결과 없음 ({})".format(scene, ours))
            continue

        entry = {"id": scene, "thumb": "static/videos/thumbs/{}.jpg".format(scene), "videos": {}}

        thumb_out = THUMB_DIR / "{}.jpg".format(scene)
        if args.force or not thumb_out.exists():
            jobs.append(("썸네일 {}".format(scene),
                         lambda s=ours, o=thumb_out: make_thumbnail(s, o, args)))

        for method_id, _label, template in METHODS:
            left = Path(str(template).format(n=scene))
            if not left.exists():
                print("  건너뜀: {} / 장면 {} — 입력 없음".format(method_id, scene))
                continue

            out = VIDEO_DIR / "{}_{}.mp4".format(method_id, scene)
            entry["videos"][method_id] = "static/videos/{}_{}.mp4".format(method_id, scene)

            if args.force or not out.exists():
                jobs.append(("{} / 장면 {}".format(method_id, scene),
                             lambda l=left, r=ours, o=out: compose(l, r, o, args)))

        if entry["videos"]:
            manifest.append(entry)

    return jobs, manifest


def write_data_js(manifest):
    data = {
        "oursLabel": OURS_LABEL,
        "teaserMethod": TEASER_METHOD,
        "methods": [{"id": m, "label": label} for m, label, _ in METHODS],
        "scenes": manifest,
    }
    DATA_JS.parent.mkdir(parents=True, exist_ok=True)
    DATA_JS.write_text(
        "/* prepare_assets.py 가 생성한 파일입니다. 직접 수정하지 마세요. */\n"
        "window.PAGE_DATA = " + json.dumps(data, indent=2, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    print("data.js 생성: {} 장면".format(len(manifest)))


def copy_figure():
    if not PIPELINE_FIGURE.exists():
        print("경고: 파이프라인 그림을 찾을 수 없습니다 ({})".format(PIPELINE_FIGURE))
        return
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    out = IMAGE_DIR / "pipeline.png"
    ok = run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(PIPELINE_FIGURE),
        "-vf", "scale='min({w},iw)':-1:flags=lanczos".format(w=PIPELINE_WIDTH), str(out),
    ])
    if not ok:
        shutil.copy2(PIPELINE_FIGURE, out)
    print("파이프라인 그림 준비 완료 ({:.0f} KB)".format(out.stat().st_size / 1024))


def get_parser():
    p = argparse.ArgumentParser(description="프로젝트 페이지용 웹 자산 생성")
    p.add_argument("--scenes", nargs="+", default=DEFAULT_SCENES,
                   help="사용할 영상 번호 (기본: 개선폭 상위 12편)")
    p.add_argument("--start", type=float, default=0.0, help="잘라낼 구간 시작 시각(초)")
    p.add_argument("--duration", type=float, default=10.0, help="잘라낼 구간 길이(초)")
    p.add_argument("--width", type=int, default=600, help="한쪽 화면의 가로 크기")
    p.add_argument("--height", type=int, default=338, help="한쪽 화면의 세로 크기")
    p.add_argument("--fps", type=int, default=30, help="출력 프레임률")
    p.add_argument("--crf", type=int, default=30, help="H.264 CRF (클수록 용량이 작다)")
    p.add_argument("--preset", default="slow", help="x264 preset")
    p.add_argument("--jobs", type=int, default=4, help="동시에 돌릴 인코딩 수")
    p.add_argument("--force", action="store_true", help="이미 있는 파일도 다시 만든다")
    return p


def main():
    args = get_parser().parse_args()

    if shutil.which("ffmpeg") is None:
        sys.exit("ffmpeg 를 찾을 수 없습니다.")

    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    THUMB_DIR.mkdir(parents=True, exist_ok=True)

    copy_figure()

    jobs, manifest = build_jobs(args.scenes, args)
    print("인코딩 대상 {}개".format(len(jobs)))

    failed = []
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {pool.submit(fn): name for name, fn in jobs}
        for future, name in futures.items():
            if not future.result():
                failed.append(name)
            else:
                print("  완료: {}".format(name))

    if failed:
        print("실패 {}건: {}".format(len(failed), ", ".join(failed)))

    write_data_js(manifest)

    total = sum(f.stat().st_size for f in VIDEO_DIR.rglob("*") if f.is_file())
    print("전체 용량: {:.1f} MB".format(total / 1024 / 1024))
    print("확인: python -m http.server 8000 --directory {}".format(PAGE_DIR))


if __name__ == "__main__":
    main()
