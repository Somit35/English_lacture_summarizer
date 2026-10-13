import os
import re
import tempfile
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import streamlit as st
import yt_dlp
from faster_whisper import WhisperModel


# ------------------------------------------
# 1. PAGE CONFIGURATION
# ------------------------------------------

st.set_page_config(
    page_title="English Lecture Summarizer",
    page_icon="📚",
    layout="wide"
)

st.title("📚 English Lecture Summarizer")
st.write(
    "Convert English lectures into text and concise study notes."
)


# ------------------------------------------
# 2. LOAD SPEECH RECOGNITION MODEL
# ------------------------------------------

@st.cache_resource(show_spinner=False)
def load_model():
    return WhisperModel(
        "base",
        device="cpu",
        compute_type="int8"
    )


# ------------------------------------------
# 3. VALIDATE YOUTUBE URL
# ------------------------------------------

def validate_youtube_url(url):
    try:
        parsed = urlparse(url.strip())
        host = (parsed.hostname or "").lower()

        valid_hosts = {
            "youtube.com",
            "www.youtube.com",
            "m.youtube.com",
            "music.youtube.com",
            "youtu.be",
            "www.youtube-nocookie.com",
            "youtube-nocookie.com",
        }

        if parsed.scheme not in ("http", "https"):
            return False

        if host not in valid_hosts:
            return False

        return True

    except Exception:
        return False


# ------------------------------------------
# 4. DOWNLOAD YOUTUBE AUDIO
# ------------------------------------------

def download_youtube_audio(url, folder):
    output_template = os.path.join(
        folder, "lecture.%(ext)s"
    )

    options = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
            }
        ],
    }

    with yt_dlp.YoutubeDL(options) as downloader:
        downloader.download([url])

    audio_files = list(
        Path(folder).glob("lecture.*")
    )

    audio_files = [
        path for path in audio_files
        if path.is_file()
        and path.suffix.lower() not in (".part", ".ytdl")
    ]

    if not audio_files:
        raise RuntimeError(
            "Audio download failed. Check the video URL "
            "and FFmpeg installation."
        )

    return str(audio_files[0])


# ------------------------------------------
# 5. TRANSCRIBE AUDIO INTO ENGLISH
# ------------------------------------------

def transcribe_audio(audio_path, progress=None):
    model = load_model()

    segments, info = model.transcribe(
        audio_path,
        language="en",
        beam_size=5,
        vad_filter=True
    )

    transcript_parts = []

    for segment in segments:
        text = segment.text.strip()

        if text:
            transcript_parts.append(text)

    transcript = " ".join(transcript_parts).strip()

    if not transcript:
        raise ValueError(
            "No speech was detected in this audio."
        )

    return transcript


# ------------------------------------------
# 6. SPLIT TRANSCRIPT INTO SENTENCES
# ------------------------------------------

def split_sentences(text):
    text = re.sub(r"\s+", " ", text).strip()

    sentences = re.split(
        r'(?<=[.!?])\s+',
        text
    )

    return [
        sentence.strip()
        for sentence in sentences
        if sentence.strip()
    ]


# ------------------------------------------
# 7. EXTRACT IMPORTANT SENTENCES
# ------------------------------------------

STOP_WORDS = set("""
a an the and or but if then else of in on at to for
from by with about as is am are was were be been being
it its this that these those he she they them their
we our you your i me my do does did have has had
can could will would should may might must not no
so very also just than too into over under after before
when where who whom which what why how all any some
such more most other same each every both few many much
there here up down out off again further once
""".split())


def summarize_text(text, sentence_count=5):
    sentences = split_sentences(text)

    if not sentences:
        return "No sentences were available to summarize."

    if len(sentences) <= sentence_count:
        return " ".join(sentences)

    # Count important words in the entire lecture.
    words = re.findall(
        r"\b[a-zA-Z]{2,}\b",
        text.lower()
    )

    frequencies = Counter(
        word for word in words
        if word not in STOP_WORDS
    )

    if not frequencies:
        return " ".join(sentences[:sentence_count])

    # Score each sentence using word frequency.
    scored_sentences = []

    for index, sentence in enumerate(sentences):
        sentence_words = re.findall(
            r"\b[a-zA-Z]{2,}\b",
            sentence.lower()
        )

        useful_words = [
            word for word in sentence_words
            if word not in STOP_WORDS
        ]

        if not useful_words:
            score = 0
        else:
            score = sum(
                frequencies[word]
                for word in useful_words
            ) / (len(useful_words) ** 0.5)

        scored_sentences.append(
            (index, sentence, score)
        )

    # Select the highest-scoring sentences.
    ranked = sorted(
        scored_sentences,
        key=lambda item: item[2],
        reverse=True
    )

    selected = ranked[:sentence_count]

    # Restore original lecture order.
    selected.sort(key=lambda item: item[0])

    return " ".join(
        item[1] for item in selected
    )


# ------------------------------------------
# 8. INPUT SELECTION
# ------------------------------------------

st.subheader("1. Choose your lecture")

input_type = st.radio(
    "Lecture source",
    ["YouTube URL", "Upload audio"],
    horizontal=True
)

youtube_url = ""
uploaded_audio = None

if input_type == "YouTube URL":
    youtube_url = st.text_input(
        "Enter YouTube lecture URL",
        placeholder="https://www.youtube.com/watch?v=..."
    )

    st.caption(
        "Use a video you can access and are permitted to process."
    )

else:
    uploaded_audio = st.file_uploader(
        "Upload an audio file",
        type=[
            "mp3", "wav", "m4a", "aac",
            "flac", "ogg", "wma", "mp4", "webm"
        ]
    )

st.subheader("2. Summary settings")

sentence_count = st.slider(
    "Number of important sentences",
    min_value=3,
    max_value=15,
    value=5
)

st.caption(
    "The summarizer selects important sentences from the transcript."
)


# ------------------------------------------
# 9. PROCESS LECTURE
# ------------------------------------------

if st.button(
    "Generate Lecture Summary",
    type="primary",
    use_container_width=True
):

    if input_type == "YouTube URL":
        if not youtube_url.strip():
            st.error("Please enter a YouTube URL.")

        elif not validate_youtube_url(youtube_url):
            st.error("Please enter a valid YouTube URL.")

        else:
            with tempfile.TemporaryDirectory() as temp_dir:
                try:
                    with st.spinner(
                        "Downloading lecture audio..."
                    ):
                        audio_path = download_youtube_audio(
                            youtube_url.strip(),
                            temp_dir
                        )

                    with st.spinner(
                        "Transcribing English lecture..."
                    ):
                        transcript = transcribe_audio(
                            audio_path
                        )

                    with st.spinner(
                        "Creating your summary..."
                    ):
                        summary = summarize_text(
                            transcript,
                            sentence_count
                        )

                    st.session_state["transcript"] = transcript
                    st.session_state["summary"] = summary

                    st.success("Lecture summarized successfully!")

                except Exception as error:
                    st.error(
                        "Could not process the YouTube video. "
                        "It may be unavailable, restricted, or "
                        "unsupported. Check the URL and try again."
                    )
                    st.caption(
                        f"Technical details: {error}"
                    )

    else:
        if uploaded_audio is None:
            st.error("Please upload an audio file.")

        else:
            with tempfile.TemporaryDirectory() as temp_dir:
                try:
                    audio_path = os.path.join(
                        temp_dir,
                        Path(uploaded_audio.name).name
                    )

                    with open(audio_path, "wb") as audio_file:
                        audio_file.write(
                            uploaded_audio.getbuffer()
                        )

                    with st.spinner(
                        "Transcribing English lecture..."
                    ):
                        transcript = transcribe_audio(
                            audio_path
                        )

                    with st.spinner(
                        "Creating your summary..."
                    ):
                        summary = summarize_text(
                            transcript,
                            sentence_count
                        )

                    st.session_state["transcript"] = transcript
                    st.session_state["summary"] = summary

                    st.success("Lecture summarized successfully!")

                except Exception as error:
                    st.error(
                        "Could not process this audio file. "
                        "Check the format and try another file."
                    )
                    st.caption(
                        f"Technical details: {error}"
                    )


# ------------------------------------------
# 10. DISPLAY AND DOWNLOAD RESULTS
# ------------------------------------------

if "summary" in st.session_state:
    st.divider()
    st.subheader("3. Lecture Summary")

    st.text_area(
        "Important points",
        value=st.session_state["summary"],
        height=200
    )

    st.download_button(
        "Download Summary (.txt)",
        data=st.session_state["summary"],
        file_name="lecture_summary.txt",
        mime="text/plain",
        use_container_width=True
    )

    st.subheader("4. Full English Transcript")

    st.text_area(
        "Transcribed lecture",
        value=st.session_state["transcript"],
        height=300
    )

    st.download_button(
        "Download Transcript (.txt)",
        data=st.session_state["transcript"],
        file_name="lecture_transcript.txt",
        mime="text/plain",
        use_container_width=True
    )


# ------------------------------------------
# 11. FOOTER
# ------------------------------------------

st.divider()

st.caption(
    "English Lecture Summarizer | Python + Streamlit "
    "+ Faster-Whisper"
)
