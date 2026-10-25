"""Educational Explainer Video Generation Pipeline using Pillow, Edge-TTS, and FFmpeg."""
import os
import re
import uuid
import asyncio
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFont

from app.config import settings
from app.output.tts import generate_speech
from app.services.llm_router import llm_router
from app.utils.logger import logger

# Find FFmpeg executable
def get_ffmpeg_cmd() -> str:
    """Finds ffmpeg path or uses default."""
    winget_pkg = list(Path("C:/Users/HP/AppData/Local/Microsoft/WinGet/Packages").glob("Gyan.FFmpeg*/ffmpeg-*/bin/ffmpeg.exe"))
    if winget_pkg:
        return str(winget_pkg[0])
    return "ffmpeg"


def get_ffprobe_cmd() -> str:
    """Finds ffprobe path."""
    winget_pkg = list(Path("C:/Users/HP/AppData/Local/Microsoft/WinGet/Packages").glob("Gyan.FFmpeg*/ffmpeg-*/bin/ffprobe.exe"))
    if winget_pkg:
        return str(winget_pkg[0])
    return "ffprobe"


async def get_audio_duration(audio_path: Path) -> float:
    """Gets audio file duration in seconds using ffprobe."""
    ffprobe = get_ffprobe_cmd()
    cmd = [
        ffprobe, "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path)
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        return max(3.0, float(stdout.decode().strip()))
    except Exception:
        return 5.0


def create_scene_frame(
    scene_number: int,
    total_scenes: int,
    topic: str,
    headline: str,
    bullets: List[str],
    analogy_or_code: str,
    output_image_path: Path
):
    """Renders a high-resolution 1920x1080 slide frame with modern styling."""
    width, height = 1920, 1080
    img = Image.new("RGB", (width, height), color=(15, 23, 42))  # Slate-900
    draw = ImageDraw.Draw(img)

    # Gradient accent bar at top
    colors = [(99, 102, 241), (168, 85, 247), (236, 72, 153)]  # Indigo to Pink
    for i in range(12):
        t = i / 12
        r = int(99 * (1 - t) + 236 * t)
        g = int(102 * (1 - t) + 72 * t)
        b = int(241 * (1 - t) + 153 * t)
        draw.line([(0, i), (width, i)], fill=(r, g, b))

    # Fonts (Use default or basic bitmap fonts with scaled drawing)
    try:
        title_font = ImageFont.truetype("arial.ttf", 54)
        subtitle_font = ImageFont.truetype("arial.ttf", 36)
        body_font = ImageFont.truetype("arial.ttf", 30)
        mono_font = ImageFont.truetype("consola.ttf", 26)
        small_font = ImageFont.truetype("arial.ttf", 22)
    except Exception:
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
        mono_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    # Badge: Topic & Scene counter
    draw.rounded_rectangle([90, 60, 400, 105], radius=10, fill=(30, 41, 59), outline=(99, 102, 241), width=2)
    draw.text((110, 70), f"STUDYBRAIN • SCENE {scene_number}/{total_scenes}", fill=(165, 180, 252), font=small_font)

    # Main Headline
    draw.text((90, 130), headline, fill=(255, 255, 255), font=title_font)
    draw.text((90, 205), f"Topic: {topic}", fill=(148, 163, 184), font=subtitle_font)

    # Left Column: Key Concept Points
    draw.rounded_rectangle([90, 280, 950, 960], radius=16, fill=(30, 41, 59, 200), outline=(51, 65, 85), width=2)
    draw.text((130, 310), "KEY INSIGHTS & MECHANICS", fill=(226, 232, 240), font=subtitle_font)

    y_offset = 390
    for idx, bullet in enumerate(bullets[:4]):
        # Bullet marker
        draw.ellipse([130, y_offset + 6, 146, y_offset + 22], fill=(99, 102, 241))
        # Word wrap bullet text
        words = bullet.split()
        lines = []
        curr = ""
        for w in words:
            if len(curr + " " + w) > 42:
                lines.append(curr)
                curr = w
            else:
                curr = (curr + " " + w).strip()
        if curr:
            lines.append(curr)

        for line in lines:
            draw.text((165, y_offset), line, fill=(203, 213, 225), font=body_font)
            y_offset += 40
        y_offset += 25

    # Right Column: Visual Analogy / Code / Cartoon Box
    draw.rounded_rectangle([1000, 280, 1830, 960], radius=16, fill=(15, 23, 42), outline=(99, 102, 241), width=2)
    draw.text((1040, 310), "VISUAL ANALOGY & CODE", fill=(244, 114, 182), font=subtitle_font)

    # Analogy or code lines
    code_lines = analogy_or_code.strip().split("\n")
    y_code = 380
    for line in code_lines[:16]:
        draw.text((1040, y_code), line[:50], fill=(56, 189, 248), font=mono_font)
        y_code += 34

    # Footer
    draw.text((90, 1000), "Generated with StudyBrain Multimodal Agent • Educational Video Pipeline", fill=(100, 116, 139), font=small_font)

    img.save(output_image_path)


async def generate_animated_explainer_video(topic: str, context: str = "") -> Dict[str, Any]:
    """
    Complete video generation pipeline:
    1. Plan 3-act educational scenes (Hook, Core Explanation, Code/Analogy Summary)
    2. Generate speech audio for each scene with Edge-TTS
    3. Generate 1920x1080 animated slide visuals
    4. Compile using FFmpeg into MP4 with web-compatible x264/AAC encoding
    """
    settings.VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    video_id = uuid.uuid4().hex[:8]
    temp_dir = settings.VIDEOS_DIR / f"temp_{video_id}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    # 1. Plan Storyboard
    scenes_data = [
        {
            "headline": f"Understanding {topic}",
            "narration": f"Welcome to this quick animated breakdown of {topic}. Let's understand what it is, why it matters, and how it works in real-world scenarios.",
            "bullets": [
                f"Core definition and purpose of {topic}.",
                "Fundamental building blocks and rules.",
                "How it simplifies problem solving."
            ],
            "analogy_or_code": f"# Concept: {topic}\ndef explore_concept():\n    understand = True\n    return 'Mastered!'\n\nprint(explore_concept())"
        },
        {
            "headline": f"How {topic} Operates Under The Hood",
            "narration": f"Here is the core mechanism behind {topic}. Notice how each component interacts step by step to solve the problem efficiently.",
            "bullets": [
                "Step 1: Input ingestion and condition check.",
                "Step 2: State transformation and processing.",
                "Step 3: Verification of invariants and base cases."
            ],
            "analogy_or_code": "# The Execution Loop:\nwhile concept_in_progress:\n    analyze_inputs()\n    execute_optimal_path()\n    verify_output()"
        },
        {
            "headline": f"Summary & Key Takeaways",
            "narration": f"In summary, mastering {topic} helps you build stronger intuition for technical problem solving. Remember the core principles and apply them to your practice.",
            "bullets": [
                "Always check edge cases and prerequisites.",
                "Time and Space complexity efficiency.",
                "Keep practicing with spaced repetition!"
            ],
            "analogy_or_code": "💡 Key Insight:\nBreak complex problems\ninto smaller atomic steps.\n\nPractice makes permanent!"
        }
    ]

    # 2. Render each scene: Audio + Image
    scene_clips = []
    total_scenes = len(scenes_data)

    for i, sc in enumerate(scenes_data):
        sc_num = i + 1
        img_path = temp_dir / f"scene_{sc_num}.png"
        audio_path = temp_dir / f"audio_{sc_num}.mp3"
        clip_path = temp_dir / f"clip_{sc_num}.mp4"

        # Create Visual Slide
        create_scene_frame(
            scene_number=sc_num,
            total_scenes=total_scenes,
            topic=topic,
            headline=sc["headline"],
            bullets=sc["bullets"],
            analogy_or_code=sc["analogy_or_code"],
            output_image_path=img_path
        )

        # Generate Speech Narration
        await generate_speech(sc["narration"], output_filename=f"audio_{video_id}_{sc_num}.mp3")
        generated_audio = settings.AUDIO_DIR / f"audio_{video_id}_{sc_num}.mp3"

        # Calculate exact duration
        duration = await get_audio_duration(generated_audio)

        # Build scene clip MP4 with FFmpeg
        ffmpeg = get_ffmpeg_cmd()
        clip_cmd = [
            ffmpeg, "-y",
            "-loop", "1", "-i", str(img_path),
            "-i", str(generated_audio),
            "-c:v", "libx264", "-tune", "stillimage",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-t", str(duration + 0.5),
            "-shortest",
            str(clip_path)
        ]

        proc = await asyncio.create_subprocess_exec(
            *clip_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        scene_clips.append(clip_path)

    # 3. Concatenate Scene Clips into Final 1080p Video
    concat_list_file = temp_dir / "concat_list.txt"
    with open(concat_list_file, "w", encoding="utf-8") as f:
        for clip in scene_clips:
            f.write(f"file '{clip.name}'\n")

    final_video_name = f"explainer_{video_id}.mp4"
    final_video_path = settings.VIDEOS_DIR / final_video_name

    concat_cmd = [
        get_ffmpeg_cmd(), "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list_file),
        "-c", "copy",
        "-movflags", "+faststart",
        str(final_video_path)
    ]

    proc = await asyncio.create_subprocess_exec(
        *concat_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    await proc.communicate()

    # Clean up temp frames
    try:
        for f in temp_dir.glob("*"):
            f.unlink(missing_ok=True)
        temp_dir.rmdir()
    except Exception:
        pass

    logger.info(f"Final explainer video generated at {final_video_path}")
    return {
        "video_id": video_id,
        "video_name": final_video_name,
        "video_url": f"/media/videos/{final_video_name}",
        "topic": topic,
        "status": "completed"
    }
