# English_lacture_summarizer
A  python project that summarizes English lecture from Youtube URLs and audio recordings.
# English Lecture Summarizer

A web application that transcribes English lectures and extracts important sentences for concise study notes.

## Features

- Process supported YouTube lecture URLs
- Upload audio files
- Transcribe English speech
- Extract important sentences automatically
- Adjust the number of summary sentences
- Download transcripts and summaries
- Access the app through a web browser

## Technologies

- Python
- Streamlit
- Faster-Whisper
- yt-dlp
- FFmpeg

## Project Structure

```text
english-lecture-summarizer/
├── app.py
├── requirements.txt
├── packages.txt
└── README.md
```

## Installation

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Install FFmpeg using your operating system's package manager.

## Run Locally

```bash
streamlit run app.py
```

## Deploy Online

1. Push this repository to GitHub.
2. Open https://share.streamlit.io/
3. Connect your GitHub account.
4. Select this repository.
5. Choose `app.py` as the main file.
6. Deploy the application.

## How It Works

Faster-Whisper converts English speech into text. An extractive summarizer ranks sentences using word frequencies and selects important points.

## Limitations

- Processing speed depends on available CPU and memory.
- Some YouTube videos may be restricted or unavailable.
- Extractive summaries use original sentences and may omit important context.
- Cloud hosting has resource and usage limits.

## License

Add a license if you want to specify how others may use or distribute this project.


