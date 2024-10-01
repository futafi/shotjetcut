from moviepy.editor import VideoFileClip
from fractions import Fraction
from pathlib import Path
from typing import Any
import ffmpeg
import webrtcvad
import wave
import contextlib

# 先ほど作成したクラス


class FileInfo:
    def __init__(self, file_path: str):
        self.path = Path(file_path)


class ClipVideo:
    def __init__(self, start: int, dur: int, src: FileInfo, offset: int, speed: float, stream: int):
        self.start = start
        self.dur = dur
        self.src = src
        self.offset = offset
        self.speed = speed
        self.stream = stream

    def to_time(self):
        # return (starttime, endtime)
        time_start = self.start / self.src.fps
        time_end = (self.start + self.dur) / self.src.fps
        return time_start, time_end


class ClipAudio:
    def __init__(self, start: int, dur: int, src: FileInfo, offset: int, speed: float, volume: float, stream: int):
        self.start = start
        self.dur = dur
        self.src = src
        self.offset = offset
        self.speed = speed
        self.volume = volume
        self.stream = stream

    def to_time(self):
        # return (starttime, endtime)
        time_start = self.start / self.src.fps
        time_end = (self.start + self.dur) / self.src.fps
        return time_start, time_end


class Video:
    def __init__(self, v, a, res, tb, sr, background, sources=None):
        self.v = v
        self.a = a
        self.res = res
        self.tb = tb
        self.sr = sr
        self.background = background
        self.sources = sources

    def _duration(self, layer: Any) -> int:
        total_dur = 0
        for clips in layer:
            dur = 0
            for clip in clips:
                dur += clip.dur
            total_dur = max(total_dur, dur)
        return total_dur

    def out_len(self) -> int:
        # Calculates the duration of the timeline
        # return max(self._duration(self.v), self._duration(self.a))
        # TODO
        return self._duration(self.v)


# # 音声トラックから盛り上がり部分を検出する関数
# def detect_high_volume_sections(audio_file, threshold_db=-20, min_duration=1.0):
#     y, sr = librosa.load(audio_file)
#     rms = librosa.feature.rms(y=y)[0]
#     db = librosa.amplitude_to_db(rms)
#
#     high_volume_sections = []
#     current_section = []
#     for i, db_level in enumerate(db):
#         time = i * (512 / sr)  # 512サンプルごとに計算
#         if db_level > threshold_db:
#             current_section.append(time)
#         else:
#             if len(current_section) > 0:
#                 if current_section[-1] - current_section[0] >= min_duration:
#                     high_volume_sections.append((current_section[0], current_section[-1]))
#                 current_section = []
#
#     return high_volume_sections


# 音声ファイルを読み込む関数
def read_wave(file_path):
    with contextlib.closing(wave.open(file_path, 'rb')) as wf:
        num_channels = wf.getnchannels()
        assert num_channels == 1, "音声ファイルはモノラルである必要があります。"
        sample_width = wf.getsampwidth()
        assert sample_width == 2, "音声ファイルのサンプル幅は16bitである必要があります。"
        sample_rate = wf.getframerate()
        assert sample_rate in (8000, 16000, 32000, 48000), "サンプルレートは8kHz, 16kHz, 32kHz, または48kHzである必要があります。"
        frames = wf.readframes(wf.getnframes())
    return frames, sample_rate


def detect_voiced_sections(file_path, aggressiveness=2, frame_duration=30, padding_duration=0.1, merge_threshold=0.15, **kwargs):
    vad = webrtcvad.Vad(aggressiveness)
    audio, sample_rate = read_wave(file_path)

    frame_size = int(sample_rate * frame_duration / 1000 * 2)
    frames = [audio[i:i + frame_size] for i in range(0, len(audio), frame_size)]

    voiced_frames = []
    for i, frame in enumerate(frames):
        if len(frame) < frame_size:
            continue
        is_speech = vad.is_speech(frame, sample_rate)
        if is_speech:
            start_time = i * frame_duration / 1000.0
            end_time = (i + 1) * frame_duration / 1000.0
            voiced_frames.append((start_time, end_time))

    # 音声区間の統合（merge_threshold以下のギャップを無視）
    high_volume_sections = []
    if voiced_frames:
        start, end = voiced_frames[0]
        for i in range(1, len(voiced_frames)):
            current_start, current_end = voiced_frames[i]
            if current_start - end <= merge_threshold:
                end = current_end
            else:
                high_volume_sections.append((max(0, start - padding_duration), end + padding_duration))
                start, end = current_start, current_end
        high_volume_sections.append((max(0, start - padding_duration), end + padding_duration))

    return high_volume_sections

###


# 動画から音声トラックを抽出し、盛り上がり部分を `ClipAudio` として処理
def process_video(video_file, audio_tracks=[0,], **kwargs):
    # 動画ファイル読み込み
    video = VideoFileClip(video_file)
    file_info = FileInfo(video_file)

    clip_audios = []
    for audio_track in audio_tracks:
        tmp_audio_file_path = f"tmp_audio_{audio_track}.wav"
        if Path(tmp_audio_file_path).exists():
            Path(tmp_audio_file_path).unlink()
        ffmpeg.input(str(video_file)).output((tmp_audio_file_path), map=f'0:a:{audio_track}', ac=1).run()

        # high_volume_sections = detect_high_volume_sections(tmp_audio_file_path, threshold_db, min_duration)
        high_volume_sections = detect_voiced_sections(tmp_audio_file_path, **kwargs)

        # 各盛り上がり部分を `ClipAudio` に変換
        for start_time, end_time in high_volume_sections:
            start_frame = int(start_time * video.fps)
            dur_frame = int((end_time - start_time) * video.fps)
            clip_audio = ClipAudio(
                start=start_frame,
                dur=dur_frame,
                src=file_info,
                offset=0,
                speed=1.0,
                volume=1.0,  # デフォルト音量
                stream=audio_track
            )
            clip_audios.append(clip_audio)

        Path(tmp_audio_file_path).unlink()

    # 映像トラックはそのまま
    clip_videos = [[ClipVideo(0, int(video.duration * video.fps), file_info, 0, 1.0, 1)]]

    # `Video` クラスにデータを格納
    video_data = Video(
        v=clip_videos,
        a=[clip_audios],
        res=(video.w, video.h),
        tb=Fraction(video.fps),
        sr=video.audio.fps,
        background="black",  # 背景色をデフォルトで黒に
        sources=[file_info]
    )

    return video_data
