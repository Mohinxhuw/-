"""Process one lecture from the command line, without Telegram. Useful for testing.

    python cli.py lecture.m4a --major medicine --out ./out
    python cli.py "https://youtu.be/..." --images slide1.jpg slide2.jpg
    python cli.py part1.m4a part2.m4a --docs slides.pptx notes.pdf
    python cli.py lecture.m4a --mock     # skip Claude, fill the PDF with placeholder content
"""
import argparse
import json
import mimetypes
from pathlib import Path

from lecturebot import materials, pipeline
from lecturebot.media import Source, download_url, find_media_url, fmt_time


def mock_analyzer(segments, major=None, images=None, duration=0.0):
    """Placeholder output built from the transcript, to test everything except the Claude call."""
    step = max(1, len(segments) // 4)
    sections = [{"heading": f"القسم {i // step + 1}", "time": fmt_time(segments[i].start),
                 "points": [{"text": s.text, "time": fmt_time(s.start)} for s in segments[i:i + step][:4]]}
                for i in range(0, len(segments), step)]
    return {
        "title": "محاضرة تجريبية", "subject": "اختبار", "overview": "محتوى تجريبي دون استدعاء Claude.",
        "sections": sections,
        "glossary": [{"term": "Example", "arabic": "مثال", "explanation": "مصطلح تجريبي."}],
        "mcq": [{"question": "سؤال تجريبي؟", "options": ["أ", "ب", "ج", "د"], "answer_index": 1,
                 "explanation": "شرح تجريبي.", "time": fmt_time(segments[0].start) if segments else "00:00"}],
        "true_false": [{"statement": "عبارة تجريبية.", "answer": True, "explanation": "شرح تجريبي.",
                        "time": fmt_time(segments[0].start) if segments else "00:00"}],
        "essay": [{"question": "سؤال مقالي تجريبي؟", "model_answer": "نموذج إجابة.", "key_points": ["نقطة"],
                   "time": "00:00"}],
        "divisions": [], "comparisons": [],
        "flashcards": [{"front": "سؤال", "back": "جواب"}],
        "transcript_fixes": [],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+", help="audio/video files or YouTube / Google Drive links, joined in order")
    ap.add_argument("--major", default=None)
    ap.add_argument("--images", nargs="*", default=[])
    ap.add_argument("--docs", nargs="*", default=[], help="PDF or PowerPoint files of the lecture")
    ap.add_argument("--out", default="out")
    ap.add_argument("--mock", action="store_true", help="skip the Claude call")
    args = ap.parse_args()

    out = Path(args.out)
    sources = []
    for i, item in enumerate(args.inputs, 1):
        url = find_media_url(item)
        sources.append(download_url(url, out / "dl", f"part{i}") if url else Source(path=Path(item), title=Path(item).stem))
    images = [(Path(p).read_bytes(), mimetypes.guess_type(p)[0] or "image/jpeg") for p in args.images]
    docs = [materials.load(Path(p).read_bytes(), Path(p).name, mimetypes.guess_type(p)[0]) for p in args.docs]

    result = pipeline.run(sources, out, major=args.major, images=images,
                          on_stage=lambda s, f: print(f"{s} {f:.0%}", end="\r", flush=True),
                          analyzer=mock_analyzer if args.mock else None, materials=docs,
                          on_section=lambda sec: print(f"\n[section] {sec.get('time', '')} {sec.get('heading', '')}"))
    (out / "analysis.json").write_text(json.dumps(result.analysis, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "transcript.txt").write_text(result.transcript_text, encoding="utf-8")
    print(f"\nPDF: {result.pdf_path}")


if __name__ == "__main__":
    main()
