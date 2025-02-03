import moviepy.editor as mpy
from pydub import AudioSegment
import numpy as np
import os
from scipy.io import wavfile
import librosa
from PIL import Image, ImageDraw, ImageFont

def detect_peaks(audio_path, threshold=0.5, min_distance=0.05):
    # Load audio file using librosa
    y, sr = librosa.load(audio_path)
    
    # Get onset strength
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    
    # Detect onset frames
    onset_frames = librosa.onset.onset_detect(
        onset_envelope=onset_env,
        sr=sr,
        wait=min_distance,  # Minimum time between onset detections (in seconds)
        pre_avg=0.5,       # Time for onset envelope moving average (in seconds)
        post_avg=0.5,      # Time for onset envelope moving average (in seconds)
        pre_max=0.5,       # Time for onset envelope maximum (in seconds)
        post_max=0.5       # Time for onset envelope maximum (in seconds)
    )
    
    # Convert frames to times
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)
    return onset_times

def create_text_image(page_words, current_word_idx, width=1280, height=720, font_size=70):
    # Create a black background
    image = Image.new('RGB', (width, height), 'black')
    draw = ImageDraw.Draw(image)
    
    # Load a font
    try:
        font = ImageFont.truetype("Arial.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    # Split words into lines based on newline markers
    lines = []
    current_line = []
    word_idx_in_line = 0
    target_line = 0
    target_word_pos = 0
    
    for i, word in enumerate(page_words):
        if word == "\n":
            if current_line:
                lines.append(current_line)
                current_line = []
                word_idx_in_line = 0
            continue
            
        current_line.append(word)
        if i == current_word_idx:
            target_line = len(lines)
            target_word_pos = word_idx_in_line
        word_idx_in_line += 1
    
    if current_line:
        lines.append(current_line)
    
    # Calculate total height of text block
    line_height = font_size * 1.5
    total_height = len(lines) * line_height
    
    # Calculate starting y position to center text block
    y = (height - total_height) // 2
    
    # Draw each line
    for i, line in enumerate(lines):
        line_text = ' '.join(line)
        bbox = draw.textbbox((0, 0), line_text, font=font)
        line_width = bbox[2] - bbox[0]
        x = (width - line_width) // 2
        
        # Draw white text
        draw.text((x, y + i * line_height), line_text, fill='white', font=font)
        
        # Draw yellow highlighted word if it's on this line
        if i == target_line and current_word_idx < len(page_words):
            before_text = ' '.join(line[:target_word_pos])
            if before_text:
                bbox_before = draw.textbbox((0, 0), before_text + ' ', font=font)
                x_yellow = x + bbox_before[2] - bbox_before[0]
            else:
                x_yellow = x
            
            current_word = line[target_word_pos]
            draw.text((x_yellow, y + i * line_height), current_word, fill='yellow', font=font)
    
    return np.array(image)

def create_karaoke_video(audio_path, syllables_file, output_path, max_words_per_page=15):
    """
    Create a karaoke video with highlighted lyrics.
    
    Args:
        audio_path: Path to the audio file
        syllables_file: Path to the file containing syllables
        output_path: Path where the output video will be saved
        max_words_per_page: Maximum number of words per page before forcing a break (default: 15)
    """
    # Load the audio file
    audio = AudioSegment.from_file(audio_path)
    
    # Read syllables from file
    with open(syllables_file, 'r', encoding='utf-8') as f:
        syllables = [line.strip() for line in f.readlines()]
    
    # Detect peaks in the audio
    onset_times = detect_peaks(audio_path)
    
    # Make sure we have enough onsets for all syllables
    if len(onset_times) < len(syllables):
        print(f"Warning: Found {len(onset_times)} onsets for {len(syllables)} syllables")
        # Use the available onsets and space out the remaining syllables
        remaining_duration = len(audio) / 1000 - onset_times[-1]
        remaining_syllables = len(syllables) - len(onset_times)
        if remaining_syllables > 0:
            extra_times = np.linspace(
                onset_times[-1],
                len(audio) / 1000,
                remaining_syllables + 1
            )[1:]
            onset_times = np.concatenate([onset_times, extra_times])
    
    # Group syllables into words and pages
    pages = []
    current_page = []
    current_word = []
    word_timings = []  # Store start time for each word
    
    # Define punctuation that indicates breaks
    break_punctuation = [',', '.', '!', ')', '?']
    
    for i, syllable in enumerate(syllables):
        # Check if this syllable starts a new line (capital letter or open parenthesis)
        starts_new_line = (syllable.strip() and 
                          (syllable.strip()[0].isupper() or 
                           syllable.strip().startswith('(')))
        
        if starts_new_line and current_page and current_word == []:
            # Add newline marker to current page
            current_page.append("\n")
        
        if syllable.endswith('-'):  # Part of a word
            current_word.append(syllable.rstrip('-'))
        else:  # End of word
            current_word.append(syllable)
            word_timings.append(onset_times[i])
            
            # Join syllables into a complete word
            complete_word = ''.join(current_word)
            current_page.append(complete_word)
            
            # Check if this word ends with break punctuation
            should_break = any(complete_word.endswith(p) for p in break_punctuation)
            
            if should_break:
                if len(current_page) > 0:
                    pages.append(current_page)
                    current_page = []
            # Fallback to prevent pages from getting too long
            elif len(current_page) >= max_words_per_page:
                pages.append(current_page)
                current_page = []
                
            current_word = []
    
    if current_page:  # Add any remaining words
        pages.append(current_page)

    # Create video clips for each page
    clips = []
    
    # Process each page
    word_idx = 0
    for page in pages:
        page_words = page
        
        # Count actual words (excluding newline markers) in this page
        actual_words = [w for w in page_words if w != "\n"]
        
        # Calculate how long this page should be displayed
        page_start_time = word_timings[word_idx]
        page_end_time = word_timings[min(word_idx + len(actual_words) - 1, len(word_timings) - 1)]
        
        # Create clips for each word change
        page_clips = []
        word_count = 0
        
        for i, word in enumerate(page_words):
            if word == "\n":
                continue
                
            current_word_idx = word_idx + word_count
            if current_word_idx >= len(word_timings):
                break
                
            # Calculate timing for this word
            word_start = word_timings[current_word_idx] - page_start_time
            if current_word_idx < len(word_timings) - 1:
                word_end = word_timings[current_word_idx + 1] - page_start_time
            else:
                word_end = page_end_time - page_start_time
            
            # Create frame with current word highlighted
            frame = create_text_image(page_words, i)
            
            # Create clip from frame
            txt_clip = mpy.ImageClip(frame).set_duration(word_end - word_start)
            txt_clip = txt_clip.set_start(word_start)
            page_clips.append(txt_clip)
            
            word_count += 1
        
        # Composite all clips for this page
        comp_clip = mpy.CompositeVideoClip(page_clips)
        comp_clip = comp_clip.set_start(page_start_time)
        clips.append(comp_clip)
        
        word_idx += len(actual_words)

    # Combine all clips
    final_video = mpy.CompositeVideoClip(clips)
    
    # Add audio
    final_video = final_video.set_audio(mpy.AudioFileClip(audio_path))
    
    # Write the final video
    final_video.write_videofile(
        output_path,
        fps=24,
        codec='libx264',
        audio_codec='aac'
    )

if __name__ == "__main__":
    audio_path = "./m4a/bon_voyage.m4a"
    syllables_file = "./lyrics/bon_voyage_no_cure_syllables.txt"
    output_path = "./videos/bon_voyage_video.mp4"
    
    create_karaoke_video(
        audio_path,
        syllables_file,
        output_path
    )