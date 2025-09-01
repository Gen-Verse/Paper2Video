
from PIL import Image
import numpy as np
from moviepy.editor import VideoFileClip, AudioFileClip, vfx, ImageClip, CompositeVideoClip, concatenate_videoclips, AudioClip, concatenate_audioclips
from moviepy.video.fx import speedx  
import re
from pathlib import Path
import base64
import io
import subprocess
from pathlib import Path
from io import BytesIO

def add_silence(audio, target_duration):
    """Pad silence at the end of the audio so that its total length matches the target duration"""
    if audio.duration >= target_duration:
        return audio  
    silence = AudioClip(
        make_frame=lambda t: [0] * audio.nchannels,
        duration=target_duration - audio.duration,
        fps=audio.fps
    )
    return concatenate_audioclips([audio, silence])

def download_video(url: str, save_dir: str, custom_name=None):
    Path(save_dir).mkdir(parents=True, exist_ok=True)
    filename = custom_name
    save_path = Path(save_dir) / filename
    subprocess.run(["wget", "-O", str(save_path), url], check=True)
    return str(save_path.resolve())

def extract_key_frames(video_path):
    clip = VideoFileClip(str(video_path))
    duration = clip.duration

    # key time
    key_times = [duration / 4, duration / 2, 3 * duration / 4]

    key_frames = []
    last_valid_frame = None

    for t in key_times:
        try:
            # 真正按时间点读取帧
            frame_np = clip.get_frame(t)              # numpy.ndarray (H, W, 3)
            frame_img = Image.fromarray(frame_np)     # convert to PIL.Image
            key_frames.append(frame_img)
            last_valid_frame = frame_img
        except Exception as e:
            print(f"Error reading frame at {t:.2f} seconds: {e}")
            key_frames.append(last_valid_frame)       # use useful frame

    clip.close()
    return key_frames

def save_video(video_path, video ):
    clip = VideoFileClip(video)
    clip.write_videofile(video_path, codec="libx264", fps=clip.fps)

def convert_frame_to_base64(frame):
    image = Image.fromarray(np.uint8(frame))  
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format="JPEG")  
    img_byte_arr.seek(0)  
    
    b64code = base64.b64encode(img_byte_arr.read()).decode()
    return f"data:image/jpeg;base64,{b64code}"

def image_to_base64(image_paths):
    result = []
    for path in image_paths:
        with Image.open(path) as img:
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            result.append(img_base64)
    return result 
    
def image_to_images(image_paths):
    """
    Read images from disk and return a list of PIL.Image objects.
    :param image_paths: list of image file paths
    :return: list of PIL.Image
    """
    images = []
    for path in image_paths:
        img = Image.open(path).convert("RGB")  # 统一为 RGB
        images.append(img)
    return images

def merge_video_audio(video_path, audio_path, text, path):
    number = float(re.search(r'\d+(?:\.\d+)?', str(text)).group())
    video_path = str(video_path)
    audio_path = str(audio_path)
    path = str(path)
    video = VideoFileClip(video_path)
    audio = AudioFileClip(audio_path)

    video_dur = video.duration
    audio_dur = audio.duration
    # compute speed
    if video_dur >  number:
        speed = min(1.5, video_dur/number)
    else:
        speed = max(1 / 1.5, video_dur/number)

    video = vfx.speedx(video, factor=speed)
    audio_dur = audio.duration
    # if audio is longer, make video longer
    if audio_dur > video.duration:
        video = vfx.speedx(video, factor=video.duration / audio_dur)
    else:
        audio = add_silence(audio, video.duration)

    final = video.set_audio(audio)
    final.write_videofile(path, codec='libx264')
    final.close()

def image_to_video(image_path, audio_path, video_duration, output_path):
    """
    merge video and audio
    :param image_path: video
    :param audio_path: audio
    :param video_duration: video duration
    :param output_path: video output path
    """
    image_path = str(image_path)
    audio_path = str(audio_path)
    output_path = str(output_path)
    video_duration = float(re.search(r'\d+(?:\.\d+)?', video_duration).group())

    video_duration = min(video_duration, 12)
    video_duration = max(video_duration, 4)

    # create ImageClip 
    image_clip = ImageClip(image_path, duration=video_duration)

    # get the height/width
    image_width, image_height = image_clip.size

    # set the resolution
    video_width, video_height = 1920, 1080

    # compute position
    x_center = (video_width - image_width) / 2
    y_center = (video_height - image_height) / 2

    # create ImageClip
    centered_image_clip = image_clip.set_position((x_center, y_center))

    # create a  CompositeVideoClip 
    video = CompositeVideoClip([centered_image_clip], size=(video_width, video_height))

    # save temp document
    temp_video_path = "temp_video.mp4"
    video.write_videofile(temp_video_path, fps=24)  # 可以根据需要调整帧率

    # use merge_video_audio to adjust time duration
    merge_video_audio(temp_video_path, audio_path, video_duration, output_path)

    # close
    video.close()
    image_clip.close()

def concatenate_videos(video_list, output_path):
    """
    将视频列表中的视频按顺序拼接成一个长视频。
    :param video_list: 视频文件路径列表
    :param output_path: 输出视频路径
    """
    # 创建一个空列表来存储视频剪辑
    clips = []
    output_path = str(output_path)
    # 遍历视频列表，加载每个视频文件
    for video_path in video_list:
        video_path = str(video_path)
        clip = VideoFileClip(video_path)
        clips.append(clip)

    # 按顺序拼接视频剪辑
    final_clip = concatenate_videoclips(clips, method="compose")

    # 保存拼接后的视频
    final_clip.write_videofile(output_path, codec="libx264", fps=24)

    # 关闭所有视频剪辑
    for clip in clips:
        clip.close()
if __name__ == "__main__":
    plan = {"scenario":"1",
            "prompt":"1",
            }
    video_path = extract_key_frames("C:\\Users\\87719\\Desktop\\AgenticIR-main\\output\\example\\scene_0\\videos\\1080p60\\scene.mp4" )




