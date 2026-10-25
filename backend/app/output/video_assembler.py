"""
KitAi Educational Explainer Video Generation Pipeline
Inspired by @cs.concepts.in.motion, 3Blue1Brown, and modern STEM visualizers.
Features:
- Dynamic LLM-driven storyboarding with real-world analogies (Groq qwen/qwen3.8-27b)
- Multi-act structure: Hook & Analogy -> Core Mechanism -> Code Execution Trace -> Key Takeaway
- Progressive kinetic animation frames (progress bar, active step pills, pointers)
- Both Landscape (16:9 HD) and Portrait Reel (9:16 Vertical for Instagram/Shorts) support
- Natural neural voiceover via Edge-TTS
- Clean H.264/AAC encoding with FFmpeg (+faststart for web streaming)
"""
import os
import re
import json
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


def get_ffmpeg_cmd() -> str:
    """Finds ffmpeg path or defaults to system ffmpeg."""
    winget_pkg = list(Path("C:/Users/HP/AppData/Local/Microsoft/WinGet/Packages").glob("Gyan.FFmpeg*/ffmpeg-*/bin/ffmpeg.exe"))
    if winget_pkg and winget_pkg[0].exists():
        return str(winget_pkg[0])
    return "ffmpeg"


def get_ffprobe_cmd() -> str:
    """Finds ffprobe path."""
    winget_pkg = list(Path("C:/Users/HP/AppData/Local/Microsoft/WinGet/Packages").glob("Gyan.FFmpeg*/ffmpeg-*/bin/ffprobe.exe"))
    if winget_pkg and winget_pkg[0].exists():
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
        val = float(stdout.decode().strip())
        return max(3.0, val)
    except Exception:
        return 5.0


def _load_font(family: str, size: int) -> ImageFont.ImageFont:
    """Safely loads TrueType fonts with fallback."""
    candidates = [
        f"C:/Windows/Fonts/{family}",
        family,
        "arial.ttf",
        "consola.ttf",
        "calibri.ttf"
    ]
    for c in candidates:
        try:
            return ImageFont.truetype(c, size)
        except Exception:
            continue
    return ImageFont.load_default()


async def generate_video_storyboard(
    topic: str,
    context: str = "",
    analogy_style: str = "daily_life"
) -> List[Dict[str, Any]]:
    """
    Uses LLM to craft an engaging 3 to 4 scene educational storyboard with:
    1. Real-life everyday analogy (kitchen, traffic, queue, library, locker)
    2. Deep mechanism & memory / execution model
    3. Step-by-step code or algorithmic trace
    4. Pro-tip & complexity takeaway
    """
    prompt = f"""You are an elite educational animator and computer science educator creating short viral concept breakdown reels (similar to @cs.concepts.in.motion and 3Blue1Brown).
Break down the requested topic into 3 to 4 sequential, high-impact animated scenes.

TOPIC: "{topic}"
ADDITIONAL CONTEXT / REQUEST: "{context}"
PREFERRED ANALOGY STYLE: "{analogy_style}" (e.g. daily life situation, kitchen/cooking, traffic/cars, store queue, school lockers).

SCENE STRUCTURE:
- Scene 1 (Hook & Everyday Analogy): Relatable real-world story explaining the core intuition.
- Scene 2 (Under The Hood / Mechanism): How the computer, algorithm, or memory handles this step by step.
- Scene 3 (Code / Logic Simulation): A clean code snippet (C++ or Python) or step-by-step trace showing the logic in motion.
- Scene 4 (Key Takeaway & Complexity): Summary, Time/Space Complexity, and a memorable pro-tip.

CRITICAL INSTRUCTIONS:
- Keep each scene narration concise (20 to 30 words) for natural speech.
- Keep bullets short (under 8 words each).
- Keep visual_content concise (under 8 lines).
- Return ONLY valid raw JSON array (no markdown backticks, no comments, no extra text).

JSON Schema:
[
  {{
    "scene_number": 1,
    "headline": "Real-Life Analogy: The Coffee Shop Line",
    "narration": "Imagine customers waiting for coffee. First come, first served. In computer science, this is a Queue!",
    "bullets": [
      "Everyday concept: First-In, First-Out (FIFO)",
      "New items join the back (Enqueue)",
      "Items leave from the front (Dequeue)"
    ],
    "visual_type": "analogy",
    "visual_title": "REAL-LIFE ANALOGY",
    "visual_content": "  [Customer 1] -> [Customer 2] -> [Customer 3]\\n  (Front/Exit)                      (Back/Enter)\\n\\n  Rule: First-In, First-Out (FIFO)"
  }}
]
"""
    try:
        response = await llm_router.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=3000
        )
        clean = response.strip()
        clean = re.sub(r"^```(?:json)?\s*", "", clean)
        clean = re.sub(r"\s*```$", "", clean)
        data = json.loads(clean)
        if isinstance(data, list) and len(data) >= 2:
            logger.info(f"Successfully generated dynamic LLM storyboard with {len(data)} scenes.")
            return data
    except Exception as e:
        logger.warning(f"Dynamic storyboard LLM parsing failed: {e}. Using high-quality curated fallback.")

    # Curated fallback template tailored to the topic
    return [
        {
            "scene_number": 1,
            "headline": f"The Real-Life Analogy of {topic}",
            "narration": f"To master {topic}, imagine an everyday scenario. When you understand the daily life metaphor, the technical implementation becomes effortless.",
            "bullets": [
                f"Relatable real-world metaphor for {topic}",
                "Breaking down the core intuition",
                "Why this pattern is so widely used"
            ],
            "visual_type": "analogy",
            "visual_title": "REAL-WORLD INTUITION",
            "visual_content": f"  [Input Request] --> [Relatable Analogy Pipeline]\n       |                          |\n       v                          v\n  [Simple Metaphor] --------> [Crystal Clear Concept]"
        },
        {
            "scene_number": 2,
            "headline": f"How {topic} Operates Under The Hood",
            "narration": f"Internally, {topic} manages state and data flow step by step. Each component communicates precisely to guarantee optimal efficiency.",
            "bullets": [
                "Step 1: Input ingestion & condition check",
                "Step 2: Processing through optimal path",
                "Step 3: Verification of invariants and state"
            ],
            "visual_type": "mechanism",
            "visual_title": "EXECUTION MECHANICS",
            "visual_content": "  1. Pointer / State Initialization\n  2. Conditional Branching Loop\n  3. State Transition & Convergence\n  4. Final Output Handshake"
        },
        {
            "scene_number": 3,
            "headline": f"Code & Algorithmic Trace",
            "narration": f"Here is how this logic translates into clean, elegant code. Notice how simple rules combine to solve complex technical challenges.",
            "bullets": [
                "Strict pedagogical coding standard",
                "Zero unnecessary overhead",
                "Optimal time and memory footprint"
            ],
            "visual_type": "code",
            "visual_title": "OPTIMAL IMPLEMENTATION",
            "visual_content": f"# Concept: {topic}\ndef solve_efficiently(data):\n    # 1. State setup\n    left, right = 0, len(data) - 1\n    while left <= right:\n        mid = (left + right) // 2\n        if check_condition(data[mid]):\n            return mid\n    return -1"
        },
        {
            "scene_number": 4,
            "headline": "Summary & Complexity Pro-Tip",
            "narration": f"Remember: always identify edge cases early. With practice and spaced repetition, applying {topic} will become second nature.",
            "bullets": [
                "Time Complexity: Highly Optimal",
                "Space Complexity: O(1) Auxiliary Memory",
                "Pro-Tip: Visualize the daily life analogy first!"
            ],
            "visual_type": "summary",
            "visual_title": "KEY TAKEAWAY",
            "visual_content": f"  ⚡ KEY FORMULA:\n  Intuition + Verified Sandbox = Mastery\n\n  Review with KitAi Spaced Repetition!"
        }
    ]


def render_landscape_frame(
    scene_number: int,
    total_scenes: int,
    topic: str,
    headline: str,
    bullets: List[str],
    visual_title: str,
    visual_content: str,
    visual_type: str,
    progress_pct: float,
    active_bullet_idx: int,
    output_path: Path
):
    """
    Renders a 1920x1080 Landscape frame with animated progress, Mac-style traffic lights,
    and progressive step highlights.
    """
    width, height = 1920, 1080
    img = Image.new("RGB", (width, height), color=(11, 15, 25))  # Ultra-dark slate backdrop
    draw = ImageDraw.Draw(img)

    # Accent Top Gradient Line (KitAi signature blue-violet-pink)
    for i in range(8):
        t = i / 8.0
        r = int(0 * (1 - t) + 67 * t)
        g = int(82 * (1 - t) + 100 * t)
        b = int(212 * (1 - t) + 247 * t)
        draw.line([(0, i), (width, i)], fill=(r, g, b))

    title_font = _load_font("segoeui.ttf", 46)
    subtitle_font = _load_font("segoeui.ttf", 28)
    body_font = _load_font("segoeui.ttf", 25)
    mono_font = _load_font("consola.ttf", 22)
    small_font = _load_font("segoeui.ttf", 20)

    # Top Header: Badge & Topic
    draw.rounded_rectangle([90, 50, 480, 95], radius=22, fill=(23, 31, 50), outline=(67, 100, 247), width=2)
    draw.ellipse([110, 68, 122, 80], fill=(67, 100, 247))  # Pulsing dot
    draw.text((135, 62), f"KITAI REEL • SCENE {scene_number} OF {total_scenes}", fill=(199, 210, 254), font=small_font)

    # Headline & Topic Subtitle
    draw.text((90, 115), headline, fill=(255, 255, 255), font=title_font)
    draw.text((90, 180), f"Topic: {topic}", fill=(148, 163, 184), font=subtitle_font)

    # Left Column: Key Insights / Mechanics Card
    draw.rounded_rectangle([90, 245, 930, 950], radius=18, fill=(19, 26, 42), outline=(42, 54, 80), width=2)
    draw.text((130, 275), "KEY INSIGHTS & MECHANICS", fill=(241, 245, 249), font=subtitle_font)

    y_offset = 350
    for idx, bullet in enumerate(bullets[:4]):
        is_active = (idx == active_bullet_idx)
        # Bullet box highlight if active
        if is_active:
            draw.rounded_rectangle([120, y_offset - 8, 900, y_offset + 52], radius=10, fill=(35, 48, 77), outline=(67, 100, 247), width=1)
            draw.text((135, y_offset + 4), "👉", fill=(255, 255, 255), font=body_font)
        else:
            draw.ellipse([140, y_offset + 12, 152, y_offset + 24], fill=(100, 116, 139))

        # Word wrapped text
        words = bullet.split()
        lines = []
        curr = ""
        for w in words:
            if len(curr + " " + w) > 38:
                lines.append(curr)
                curr = w
            else:
                curr = (curr + " " + w).strip()
        if curr:
            lines.append(curr)

        text_x = 175 if is_active else 170
        text_color = (255, 255, 255) if is_active else (203, 213, 225)
        for line in lines:
            draw.text((text_x, y_offset + 4), line, fill=text_color, font=body_font)
            y_offset += 32
        y_offset += 28

    # Right Column: Visual Analogy / Code Window Card (with Mac Traffic Lights)
    draw.rounded_rectangle([970, 245, 1830, 950], radius=18, fill=(13, 18, 30), outline=(67, 100, 247), width=2)

    # Traffic light controls
    draw.ellipse([1005, 275, 1021, 291], fill=(239, 68, 68))    # Red
    draw.ellipse([1031, 275, 1047, 291], fill=(234, 179, 8))    # Yellow
    draw.ellipse([1057, 275, 1073, 291], fill=(34, 197, 94))    # Green

    box_title = visual_title if visual_title else ("VISUAL ANALOGY" if visual_type == "analogy" else "CODE SIMULATION")
    draw.text((1100, 270), box_title, fill=(244, 114, 182), font=subtitle_font)

    # Visual / Code Content
    code_lines = visual_content.strip().split("\n")
    y_code = 345
    for l_idx, line in enumerate(code_lines[:17]):
        # Light highlighting for active code lines
        color = (56, 189, 248)  # Cyan
        if visual_type == "code" and (l_idx == 4 or l_idx == 5):
            color = (250, 204, 21)  # Yellow highlight on active loop
        elif line.strip().startswith("#") or line.strip().startswith("//"):
            color = (148, 163, 184)  # Muted grey for comments
        elif "return" in line or "def " in line or "while" in line:
            color = (192, 132, 252)  # Purple keyword

        draw.text((1010, y_code), line[:60], fill=color, font=mono_font)
        y_code += 33

    # Footer Branding
    draw.text((90, 995), "KitAi • Autonomous Educational Media Pipeline • Verified Sandbox", fill=(100, 116, 139), font=small_font)

    # Dynamic Bottom Progress Bar (smoothly fills from 0 to 1920)
    bar_width = int(width * max(0.02, min(1.0, progress_pct)))
    draw.rectangle([0, 1068, width, 1080], fill=(20, 26, 40))
    for px in range(bar_width):
        t = px / float(width)
        r = int(0 * (1 - t) + 111 * t)
        g = int(82 * (1 - t) + 177 * t)
        b = int(212 * (1 - t) + 252 * t)
        draw.line([(px, 1068), (px, 1080)], fill=(r, g, b))

    img.save(output_path, "PNG")


def render_portrait_frame(
    scene_number: int,
    total_scenes: int,
    topic: str,
    headline: str,
    bullets: List[str],
    visual_title: str,
    visual_content: str,
    visual_type: str,
    progress_pct: float,
    active_bullet_idx: int,
    output_path: Path
):
    """
    Renders a 1080x1920 Portrait Reel (9:16 Vertical) optimized for Instagram Reels,
    YouTube Shorts, and mobile learning.
    """
    width, height = 1080, 1920
    img = Image.new("RGB", (width, height), color=(11, 15, 25))
    draw = ImageDraw.Draw(img)

    # Accent Top Gradient Line
    for i in range(10):
        t = i / 10.0
        r = int(0 * (1 - t) + 67 * t)
        g = int(82 * (1 - t) + 100 * t)
        b = int(212 * (1 - t) + 247 * t)
        draw.line([(0, i), (width, i)], fill=(r, g, b))

    title_font = _load_font("segoeui.ttf", 48)
    subtitle_font = _load_font("segoeui.ttf", 32)
    body_font = _load_font("segoeui.ttf", 28)
    mono_font = _load_font("consola.ttf", 24)
    small_font = _load_font("segoeui.ttf", 22)

    # Header: KitAi Reel Badge
    draw.rounded_rectangle([60, 60, 480, 115], radius=24, fill=(23, 31, 50), outline=(67, 100, 247), width=2)
    draw.ellipse([85, 80, 99, 94], fill=(67, 100, 247))
    draw.text((115, 75), f"KITAI REEL • {scene_number}/{total_scenes}", fill=(199, 210, 254), font=small_font)

    # Headline
    draw.text((60, 140), headline, fill=(255, 255, 255), font=title_font)
    draw.text((60, 205), f"Topic: {topic}", fill=(148, 163, 184), font=subtitle_font)

    # Center Visual Card (Mac Traffic Lights + Analogy/Code Box)
    draw.rounded_rectangle([60, 275, 1020, 1020], radius=20, fill=(13, 18, 30), outline=(67, 100, 247), width=2)
    draw.ellipse([95, 305, 111, 321], fill=(239, 68, 68))
    draw.ellipse([121, 305, 137, 321], fill=(234, 179, 8))
    draw.ellipse([147, 305, 163, 321], fill=(34, 197, 94))

    box_title = visual_title if visual_title else ("VISUAL ANALOGY" if visual_type == "analogy" else "CODE SIMULATION")
    draw.text((190, 300), box_title, fill=(244, 114, 182), font=subtitle_font)

    code_lines = visual_content.strip().split("\n")
    y_code = 380
    for l_idx, line in enumerate(code_lines[:15]):
        color = (56, 189, 248)
        if "return" in line or "def " in line or "while" in line:
            color = (192, 132, 252)
        elif line.strip().startswith("#"):
            color = (148, 163, 184)
        draw.text((95, y_code), line[:44], fill=color, font=mono_font)
        y_code += 40

    # Bottom Mechanics & Bullets Card
    draw.rounded_rectangle([60, 1070, 1020, 1770], radius=20, fill=(19, 26, 42), outline=(42, 54, 80), width=2)
    draw.text((100, 1105), "KEY TAKEAWAYS & LOGIC", fill=(241, 245, 249), font=subtitle_font)

    y_offset = 1180
    for idx, bullet in enumerate(bullets[:4]):
        is_active = (idx == active_bullet_idx)
        if is_active:
            draw.rounded_rectangle([90, y_offset - 8, 990, y_offset + 64], radius=12, fill=(35, 48, 77), outline=(67, 100, 247), width=1)
            draw.text((110, y_offset + 10), "👉", fill=(255, 255, 255), font=body_font)
        else:
            draw.ellipse([115, y_offset + 20, 127, y_offset + 32], fill=(100, 116, 139))

        words = bullet.split()
        lines = []
        curr = ""
        for w in words:
            if len(curr + " " + w) > 34:
                lines.append(curr)
                curr = w
            else:
                curr = (curr + " " + w).strip()
        if curr:
            lines.append(curr)

        text_x = 155 if is_active else 150
        text_color = (255, 255, 255) if is_active else (203, 213, 225)
        for line in lines:
            draw.text((text_x, y_offset + 8), line, fill=text_color, font=body_font)
            y_offset += 38
        y_offset += 30

    # Footer Branding
    draw.text((60, 1820), "KitAi • Autonomous Educational Media Pipeline", fill=(100, 116, 139), font=small_font)

    # Dynamic Bottom Progress Bar
    bar_width = int(width * max(0.02, min(1.0, progress_pct)))
    draw.rectangle([0, 1905, width, 1920], fill=(20, 26, 40))
    for px in range(bar_width):
        t = px / float(width)
        r = int(0 * (1 - t) + 111 * t)
        g = int(82 * (1 - t) + 177 * t)
        b = int(212 * (1 - t) + 252 * t)
        draw.line([(px, 1905), (px, 1920)], fill=(r, g, b))

    img.save(output_path, "PNG")


async def generate_animated_explainer_video(
    topic: str,
    context: str = "",
    orientation: str = "landscape",
    analogy_style: str = "daily_life"
) -> Dict[str, Any]:
    """
    Generates a full educational explainer video:
    1. AI-driven storyboard generation with real-world analogies
    2. High-fidelity neural voiceover synthesis (Edge-TTS)
    3. Multi-frame kinetic animation (progressive timeline bar + active step highlight)
    4. FFmpeg encoding with H.264 / AAC and faststart streaming flags
    """
    settings.VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    video_id = uuid.uuid4().hex[:8]
    temp_dir = settings.VIDEOS_DIR / f"temp_{video_id}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    is_portrait = (orientation.lower() in ("portrait", "reel", "vertical", "9:16"))

    # 1. Generate Intelligent Storyboard
    logger.info(f"Generating storyboard for '{topic}' (Orientation: {orientation}, Style: {analogy_style})...")
    scenes_data = await generate_video_storyboard(topic=topic, context=context, analogy_style=analogy_style)
    total_scenes = len(scenes_data)

    scene_clips = []
    total_duration = 0.0

    # 2. Render each scene with progressive kinetic animation
    for i, sc in enumerate(scenes_data):
        sc_num = i + 1
        scene_dir = temp_dir / f"scene_{sc_num}"
        scene_dir.mkdir(parents=True, exist_ok=True)

        headline = sc.get("headline", f"Step {sc_num}: {topic}")
        narration = sc.get("narration", f"Let's explore {topic}.")
        bullets = sc.get("bullets", ["Key concept", "Mechanics", "Summary"])
        visual_type = sc.get("visual_type", "analogy")
        visual_title = sc.get("visual_title", "VISUAL CONCEPT")
        visual_content = sc.get("visual_content", f"# {topic}\ndef run():\n    return True")

        # Generate Audio
        audio_filename = f"audio_{video_id}_{sc_num}.mp3"
        await generate_speech(narration, output_filename=audio_filename)
        audio_path = settings.AUDIO_DIR / audio_filename
        duration = await get_audio_duration(audio_path)
        total_duration += duration

        # Generate 12 progressive animation frames for this scene
        num_frames = 12
        frame_paths = []
        for f_idx in range(num_frames):
            progress_pct = (f_idx + 1) / float(num_frames)
            active_bullet = min(len(bullets) - 1, int(progress_pct * len(bullets)))
            frame_path = scene_dir / f"frame_{f_idx:03d}.png"

            if is_portrait:
                render_portrait_frame(
                    scene_number=sc_num,
                    total_scenes=total_scenes,
                    topic=topic,
                    headline=headline,
                    bullets=bullets,
                    visual_title=visual_title,
                    visual_content=visual_content,
                    visual_type=visual_type,
                    progress_pct=progress_pct,
                    active_bullet_idx=active_bullet,
                    output_path=frame_path
                )
            else:
                render_landscape_frame(
                    scene_number=sc_num,
                    total_scenes=total_scenes,
                    topic=topic,
                    headline=headline,
                    bullets=bullets,
                    visual_title=visual_title,
                    visual_content=visual_content,
                    visual_type=visual_type,
                    progress_pct=progress_pct,
                    active_bullet_idx=active_bullet,
                    output_path=frame_path
                )
            frame_paths.append(frame_path)

        # Build scene clip with FFmpeg using frame sequence
        clip_path = temp_dir / f"clip_{sc_num}.mp4"
        framerate = num_frames / max(1.0, duration)
        ffmpeg = get_ffmpeg_cmd()

        clip_cmd = [
            ffmpeg, "-y",
            "-framerate", str(framerate),
            "-i", str(scene_dir / "frame_%03d.png"),
            "-i", str(audio_path),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(clip_path)
        ]

        proc = await asyncio.create_subprocess_exec(
            *clip_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        scene_clips.append(clip_path)

    # 3. Concatenate Scene Clips into Final Video
    concat_list_file = temp_dir / "concat_list.txt"
    with open(concat_list_file, "w", encoding="utf-8") as f:
        for clip in scene_clips:
            f.write(f"file '{clip.name}'\n")

    orientation_suffix = "reel" if is_portrait else "landscape"
    final_video_name = f"kitai_{orientation_suffix}_{video_id}.mp4"
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
        for p in temp_dir.rglob("*"):
            if p.is_file():
                p.unlink(missing_ok=True)
        for p in sorted(temp_dir.rglob("*"), reverse=True):
            if p.is_dir():
                p.rmdir()
        temp_dir.rmdir()
    except Exception:
        pass

    logger.info(f"Final explainer video generated at {final_video_path} (Duration: {total_duration:.1f}s)")
    return {
        "video_id": video_id,
        "video_name": final_video_name,
        "video_url": f"/media/videos/{final_video_name}",
        "topic": topic,
        "orientation": orientation_suffix,
        "scenes_count": total_scenes,
        "duration_seconds": round(total_duration, 1),
        "status": "completed",
        "storyboard": scenes_data
    }
