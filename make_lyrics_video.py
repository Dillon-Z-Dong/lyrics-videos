import moviepy.editor as mpy
from pydub import AudioSegment
import numpy as np
import os
from scipy.io import wavfile
import librosa

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

def create_karaoke_video(audio_path, syllables_file, output_path, words_per_page=10):
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
    word_count = 0
    current_word = []
    word_timings = []  # Store start time for each word
    
    for i, syllable in enumerate(syllables):
        if syllable.endswith('-'):  # Part of a word
            current_word.append(syllable.rstrip('-'))
        else:  # End of word
            current_word.append(syllable)
            word_timings.append(onset_times[i])  # Store the timing of the last syllable in word
            word_count += 1
            
            # Join syllables into a complete word
            complete_word = ''.join(current_word)
            
            if word_count >= words_per_page:
                current_page.append(complete_word)
                pages.append(current_page)
                current_page = []
                word_count = 0
            else:
                current_page.append(complete_word)
            current_word = []
    
    if current_page:  # Add any remaining words
        pages.append(current_page)

    # Create video clips for each page
    clips = []
    
    # Process each page
    word_idx = 0
    for page in pages:
        page_words = page
        
        # Calculate how long this page should be displayed
        page_start_time = word_timings[word_idx]
        page_end_time = word_timings[min(word_idx + len(page_words) - 1, len(word_timings) - 1)]
        
        # Create background clip (all words in white)
        bg_txt_clip = mpy.TextClip(
            txt=' '.join(page_words),
            fontsize=70,
            color='white',
            bg_color='black',
            size=(1280, 720),
            method='caption',
            align='center'
        ).set_duration(page_end_time - page_start_time)
        
        # Create individual clips for each word in yellow
        word_clips = []
        for i, word in enumerate(page_words):
            current_word_idx = word_idx + i
            if current_word_idx >= len(word_timings):
                break
                
            # Calculate timing for this word
            word_start = word_timings[current_word_idx] - page_start_time
            if current_word_idx < len(word_timings) - 1:
                word_end = word_timings[current_word_idx + 1] - page_start_time
            else:
                word_end = page_end_time - page_start_time
            
            # Create a clip for this word
            spaces_before = ' ' * len(' '.join(page_words[:i]))
            if i > 0:
                spaces_before += ' '
            spaces_after = ' ' * len(' '.join(page_words[i+1:]))
            
            word_txt_clip = mpy.TextClip(
                txt=spaces_before + word + spaces_after,
                fontsize=70,
                color='yellow',
                bg_color='rgba(0,0,0,0)',
                size=(1280, 720),
                method='caption',
                transparent=True,
                align='center'
            ).set_duration(word_end - word_start)
            
            word_txt_clip = word_txt_clip.set_start(word_start)
            word_clips.append(word_txt_clip)
        
        # Composite all clips for this page
        page_clips = [bg_txt_clip] + word_clips
        comp_clip = mpy.CompositeVideoClip(page_clips)
        comp_clip = comp_clip.set_start(page_start_time)
        clips.append(comp_clip)
        
        word_idx += len(page_words)

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
    
    create_karaoke_video(audio_path, syllables_file, output_path)