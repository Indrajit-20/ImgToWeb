import os
import io
import traceback
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PIL import Image
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# ── Gemini setup ──────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not set in environment variables.")

client = genai.Client(api_key=GEMINI_API_KEY)

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Image → Website Generator",
    description="Upload a screenshot/wireframe and get production-ready HTML/CSS/JS",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Constants ─────────────────────────────────────────────────────────────────
MAX_FILE_SIZE_MB = 10
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

VALIDATE_PROMPT = """Look at this image carefully and answer ONE question:

Is this image a website screenshot, web UI design, wireframe, app mockup, landing page design, dashboard design, or any kind of web/app interface?

Reply with ONLY one of these two responses — nothing else:
VALID
INVALID: <one short reason why, max 8 words>

Examples of VALID: website screenshot, landing page design, wireframe, app UI, dashboard mockup
Examples of INVALID: selfie photo, nature photo, document scan, logo only, meme, desktop file explorer, random screenshot of non-web content"""

GENERATE_PROMPT = """You are an expert frontend developer.
Analyze this image carefully and convert it into a complete, production-ready single HTML file.

Requirements:
1. Output ONLY raw HTML — no markdown, no code fences, no explanation.
2. Include all CSS inside a <style> tag in <head>.
3. Include all JavaScript inside a <script> tag before </body>.
4. Make it fully responsive (mobile-first).
5. Use modern CSS (flexbox/grid, CSS variables, smooth transitions).
6. Preserve the layout, colors, fonts, and structure shown in the image as closely as possible.
7. Add subtle hover effects and polish where appropriate.
8. The page must work with zero external dependencies (no CDN links unless clearly shown in the image).

Hard rules (important for iframe embedding):
9. Do NOT include ANY absolute URLs. Do NOT include http://, https://, //, localhost, 0.0.0.0, or LAN IPs in href/src/action.
10. Do NOT include <iframe>, <object>, <embed>, or navigation that changes window.location.
11. If you need assets, inline them (e.g., data: URLs) or avoid external requests.
12. Use only relative paths if absolutely required (prefer inlining instead).

Output the complete HTML document starting with <!DOCTYPE html> and nothing else."""

# ── Helpers ───────────────────────────────────────────────────────────────────

def optimize_image(file_bytes: bytes) -> tuple[bytes, str]:
    """Resize, convert to WebP, and return optimized bytes + mime type."""
    img = Image.open(io.BytesIO(file_bytes))

    if img.mode in ("RGBA", "P", "LA"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        background.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    max_dim = 1280
    w, h = img.size
    if w > max_dim or h > max_dim:
        ratio = min(max_dim / w, max_dim / h)
        img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

    buffer = io.BytesIO()
    img.save(buffer, format="WEBP", quality=85)
    return buffer.getvalue(), "image/webp"


def validate_image(image_bytes: bytes, mime_type: str) -> tuple[bool, str]:
    """Ask Gemini if the image is a valid web UI / screenshot."""
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            types.Part.from_text(text=VALIDATE_PROMPT),
        ],
        config=types.GenerateContentConfig(
            temperature=0,
            max_output_tokens=50,
        ),
    )
    answer = response.text.strip()
    if answer.upper().startswith("VALID"):
        return True, ""
    # Extract reason after "INVALID: "
    reason = answer.split(":", 1)[-1].strip() if ":" in answer else "Not a web UI or website screenshot"
    return False, reason


def call_gemini(image_bytes: bytes, mime_type: str) -> str:
    """Send image to Gemini and return the raw HTML string."""
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            types.Part.from_text(text=GENERATE_PROMPT),
        ],
        config=types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=8192,
        ),
    )
    html = response.text.strip()
    if html.startswith("```"):
        lines = html.split("\n")
        html = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return html


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "ok", "message": "Image → Website API is running 🚀"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/generate")
async def generate(file: UploadFile = File(...)):
    # 1 — Check file type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{file.content_type}'. Please upload a JPEG, PNG, WEBP, or GIF image.",
        )

    # 2 — Check file size
    file_bytes = await file.read()
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_mb:.1f} MB). Maximum allowed size is {MAX_FILE_SIZE_MB} MB.",
        )

    try:
        # 3 — Optimize with Pillow
        optimized_bytes, mime = optimize_image(file_bytes)

        # 4 — Validate: is this actually a web UI image?
        is_valid, reason = validate_image(optimized_bytes, mime)
        if not is_valid:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid image: {reason}. Please upload a website screenshot, wireframe, or UI design.",
            )

        # 5 — Generate HTML
        html_output = call_gemini(optimized_bytes, mime)

        return JSONResponse({
            "success": True,
            "html": html_output,
            "original_size_kb": round(len(file_bytes) / 1024, 1),
            "optimized_size_kb": round(len(optimized_bytes) / 1024, 1),
        })

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")
