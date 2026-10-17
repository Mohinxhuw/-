"""Process one lecture from the command line, without Telegram. Useful for testing.

    python cli.py lecture.m4a --major medicine --out ./out
    python cli.py "https://youtu.be/..." --images slide1.jpg slide2.jpg
    python cli.py lecture.m4a --mock     # skip Claude, fill the PDF with placeholder content
"""
import argparse
import json
import mimetypes
from pathlib import Path

from lecturebot import pipeline
from lecturebot.media import Source, download_youtube, find_youtube_url, fmt_time


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
        "flashcards": [{"front": "سؤال", "back": "جواب"}],
        "transcript_fixes": [],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="audio/video file or YouTube URL")
    ap.add_argument("--major", default=None)
    ap.add_argument("--images", nargs="*", default=[])
    ap.add_argument("--out", default="out")
    ap.add_argument("--mock", action="store_true", help="skip the Claude call")
    args = ap.parse_args()

    out = Path(args.out)
    url = find_youtube_url(args.input)
    source = download_youtube(url, out / "dl") if url else Source(path=Path(args.input), title=Path(args.input).stem)
    images = [(Path(p).read_bytes(), mimetypes.guess_type(p)[0] or "image/jpeg") for p in args.images]

    result = pipeline.run(source, out, major=args.major, images=images,
                          on_stage=lambda s, f: print(f"{s} {f:.0%}", end="\r", flush=True),
                          analyzer=mock_analyzer if args.mock else None)
    (out / "analysis.json").write_text(json.dumps(result.analysis, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "transcript.txt").write_text(result.transcript_text, encoding="utf-8")
    print(f"\nPDF: {result.pdf_path}")


if __name__ == "__main__":
    main()
