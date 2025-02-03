# Lyrics Video Generator

A Python script that generates karaoke-style videos from audio files and syllable-separated lyrics.

## Prerequisites

Before installing the Python dependencies from `requirements.txt`, you'll need to install some system-level dependencies.

### MacOS

Using Homebrew:

```bash
# Install FFmpeg (required for video processing)
brew install ffmpeg

# Install portaudio (required for audio processing)
brew install portaudio

# Install libsndfile (required for audio file handling)
brew install libsndfile
```

### Windows

1. Install FFmpeg:
   - Download the latest FFmpeg build from [https://github.com/BtbN/FFmpeg-Builds/releases](https://github.com/BtbN/FFmpeg-Builds/releases)
   - Download the `ffmpeg-master-latest-win64-gpl.zip` file
   - Extract the contents
   - Add the `bin` folder to your system's PATH environment variable

2. Install libsndfile:
   - Download the latest version from [https://github.com/libsndfile/libsndfile/releases](https://github.com/libsndfile/libsndfile/releases)
   - Download the Windows 64-bit installer
   - Run the installer
   - Add the installation directory to your system's PATH environment variable

## Python Dependencies

After installing the system dependencies, install the Python packages:

```bash
pip install -r requirements.txt
```

## Usage

Place your audio files in the `m4a` directory and your syllable-separated lyrics files in the `lyrics` directory. The output videos will be generated in the `videos` directory.

Run the script:

```bash
python main.py
```

## File Structure

- `m4a/`: Directory for audio files
- `lyrics/`: Directory for syllable-separated lyrics files
- `videos/`: Directory for output video files

## Example Lyrics File Format

Your lyrics file should have syllables separated by newlines, with hyphens indicating syllable breaks within words:

```
wel-
come
to
the
show
```