import re
import sys
from datetime import time, datetime, timedelta


type VttData = list[tuple[time, time, str]]


def add_seconds(t: time, seconds: float) -> time:
    """Add a number of seconds to a time object.

    Args:
        t: The time object to add seconds to
        seconds: The number of seconds to add (can be negative)

    Returns:
        A new time object with the seconds added
    """
    dt = datetime.combine(datetime.today(), t)
    dt_plus_sec = dt + timedelta(seconds=seconds)
    return dt_plus_sec.time()


def str_to_time(text: str) -> time | None:
    """Convert a string to a time object.

    Args:
        text: String in ISO format (HH:MM:SS)

    Returns:
        A time object if parsing succeeds, None otherwise
    """
    try:
        return time.fromisoformat(text)
    except ValueError:
        return None


def read_raw_data(filename: str) -> VttData:
    """Read raw subtitle data from a file and convert to VTT format.

    The file should contain timestamps and text lines. Timestamps mark
    the start of new subtitle segments.

    Args:
        file: Path to the input file

    Returns:
        List of tuples containing (start_time, end_time, text)
    """
    result = []
    with open(filename, "r", encoding="utf-8") as file:
        start_time = time(0, 0, 0, 0)
        texts: list[str] = []
        for line in file:
            clean_line = line.strip()
            the_time = str_to_time(clean_line)
            if the_time is not None and len(texts) == 0:
                continue
            elif the_time is not None:
                end_time = add_seconds(the_time, -0.5)
                result.append((start_time, end_time, " ".join(texts)))
                start_time = the_time
                texts = []
            else:
                texts.append(clean_line)
        if len(texts) != 0:
            # TODO: should not always add 5 seconds
            result.append((start_time, add_seconds(start_time, 5), " ".join(texts)))
    return result


def split_subtitles(vtt: VttData) -> VttData:
    """Split long subtitles into smaller chunks.

    Subtitles longer than 120 characters are split into multiple subtitles.

    Args:
        vtt: List of subtitle tuples

    Returns:
        List of subtitle tuples with long subtitles split
    """
    output = []
    for s, e, t in vtt:
        if len(t) <= 60 * 2:
            output.append((s, e, t))
        else:
            output.extend(split_subtitle(s, e, t))
    return output


def split_subtitle(start: time, end: time, text: str) -> VttData:
    """Split a single long subtitle into multiple subtitles.

    Args:
        start: Start time of the subtitle
        end: End time of the subtitle
        text: Text content to split

    Returns:
        List of subtitle tuples with split content and times
    """
    lines = split_text_by_sentences(text)
    times = split_time(start, end, len(lines))
    return [(s, e, line) for (line, (s, e)) in zip(lines, times)]


def time_to_seconds(t):
    """Convert a time object to total seconds.

    Args:
        t: Time object to convert

    Returns:
        Total seconds as integer
    """
    return t.hour * 3600 + t.minute * 60 + t.second


def split_time(start: time, end: time, count: int) -> zip[tuple[time, time]]:
    """Split a time range into multiple segments.

    If possible each segment will have an duration of ten seconds
    (except for the last segment that will have all the remaining time).
    If the duration is too small for that each segment is given equal time.

    Args:
        start: Start time of the range
        end: End time of the range
        count: Number of segments to create

    Returns:
        List of (start_time, end_time) tuples for each segment
    """
    start_seconds = time_to_seconds(start)
    end_seconds = time_to_seconds(end)
    total_duration = end_seconds - start_seconds

    # if too small, just split evenly
    time_allotment = min(10, total_duration // count)
    start_times = [
        add_seconds(start, seconds) for seconds in range(0, end_seconds, time_allotment)
    ]

    # since we might have some overflow
    start_times = start_times[:count]
    end_times = start_times[1:]
    end_times.append(end)

    return zip(start_times, end_times)


def split_text_by_sentences(text, max_length=120):
    """Split text into chunks at sentence boundaries.

    Attempts to break text at sentence endings within the max_length limit.
    Falls back to word boundaries if no sentence end is found.

    Args:
        text: Text to split
        max_length: Maximum length of each chunk

    Returns:
        List of text chunks
    """
    chunks = []
    start = 0
    while start < len(text):
        # if the remaining text is short, take it all
        if len(text) - start <= max_length:
            chunks.append(text[start:].strip())
            break
        # try to find a sentence end within the next max_length chars
        end = end_of_sentence_before(text, start + max_length + 1)
        if end == -1 or end < start:
            end = start + max_length
            # avoid breaking in the middle of a word
            while end > start and text[end - 1] not in " \n":
                end -= 1
        else:
            end += 1
        chunks.append(text[start:end].strip())
        start = end
    return chunks


def end_of_sentence_before(text, pos):
    """Find the last sentence ending before a given position.

    Args:
        text: Text to search in
        pos: Position to search backwards from

    Returns:
        Index of the last sentence ending character, or -1 if none found
    """
    for i in range(pos - 1, -1, -1):
        if text[i] in ".?!,":
            return i
    return -1


def split_into_lines(text: str) -> list[str]:
    """Split text into lines with a maximum length of 60 characters.

    Breaks text at word boundaries to avoid splitting words across lines.

    Args:
        text: Text to split into lines

    Returns:
        List of lines, each 60 characters or less
    """
    words = re.split(r"\s+", text)

    lines = []
    current_line = ""

    for word in words:
        word = word.strip()
        if not word:
            continue

        # if adding this word would exceed 60 characters, start a new line
        if current_line and len(current_line + " " + word) > 60:
            lines.append(current_line)
            current_line = word
        # if current line is empty, start with this word
        elif not current_line:
            current_line = word
        else:
            current_line += " " + word

    if current_line:
        lines.append(current_line)

    return lines


def output_vtt(data: VttData, filename: str):
    """Write subtitle data to a WebVTT format file.

    Args:
        data: List of subtitle tuples (start_time, end_time, text)
        filename: Output file path
    """
    with open(filename, "w", encoding="utf-8") as file:
        file.write("WEBVTT\n\n")
        for s, e, t in data:
            start = f"{s.hour:0>2}:{s.minute:0>2}:{s.second:0>2}.{s.microsecond // 1000:0<3}"
            end = f"{e.hour:0>2}:{e.minute:0>2}:{e.second:0>2}.{e.microsecond // 1000:0<3}"

            file.write(start)
            file.write(" --> ")
            file.write(end)
            file.write("\n")
            for line in split_into_lines(t):
                file.write(line)
                file.write("\n")
            file.write("\n")


def main():
    if len(sys.argv) != 2:
        print("You must give a file to convert")
        exit(-1)

    filename = sys.argv[1]
    raw_data = read_raw_data(filename)
    fixed_data = split_subtitles(raw_data)
    output_vtt(fixed_data, filename + ".vtt")


if __name__ == "__main__":
    main()
