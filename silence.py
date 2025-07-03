from pydub import AudioSegment
from pydub.silence import detect_silence

def detect_silent_segments(mp3_path: str, silence_thresh_db: int = -40, min_silence_len_ms: int = 500) -> None:
    audio = AudioSegment.from_mp3(mp3_path)

    silent_ranges = detect_silence(
        audio,
        min_silence_len=min_silence_len_ms,
        silence_thresh=silence_thresh_db
    )

    print("Silent segments (start, end) in seconds:")
    for start_ms, end_ms in silent_ranges:
        print(f"{start_ms / 1000:.2f} - {end_ms / 1000:.2f}")

if __name__ == "__main__":
    detect_silent_segments("audiotest.mp3")
