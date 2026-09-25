"""Digital stand-ins for a scanned or phone-photographed CV (T028).

A scan is every page rasterised, tilted, greyed, grained and stored as JPEG inside an image-only
PDF, the way an office scanner saves one. A photograph is one page laid on a desk in perspective,
unevenly lit, slightly soft and saved as a phone-sized JPEG. Neither carries a text layer, so
extraction has to read the pixels, which is what SC-003 measures.

They stand in for the real thing until real scans and photos arrive, and are labelled as simulated
so the accuracy gate can tell them apart. The same seed always gives the same pixels.
"""

import io
import math
import random
from pathlib import Path

import pymupdf
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter

SCAN_DPI = 150
PHOTO_SIZE = (1536, 2048)  # a 3:4 phone photo
Point = tuple[float, float]


def _render(page: pymupdf.Page, dpi: int) -> Image.Image:
    pixmap = page.get_pixmap(dpi=dpi, alpha=False)
    return Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)


def _grain(size: tuple[int, int], rng: random.Random) -> Image.Image:
    """Uniform grey noise, reproducible from the seed unlike Pillow's own noise."""
    return Image.frombytes("L", size, rng.randbytes(size[0] * size[1]))


def _scan_page(page: Image.Image, rng: random.Random) -> Image.Image:
    grey = page.convert("L")
    grey = grey.rotate(rng.uniform(-1.2, 1.2), Image.Resampling.BICUBIC, fillcolor=255)
    grey = ImageEnhance.Contrast(grey).enhance(1.15)
    grey = ImageEnhance.Brightness(grey).enhance(0.97)
    grey = Image.blend(grey, _grain(grey.size, rng), 0.05)
    # The dark band a scanner lid leaves where the paper stops short of the glass.
    band = rng.randint(4, 9)
    ImageDraw.Draw(grey).rectangle((0, 0, grey.width, band), fill=rng.randint(70, 110))
    return grey.filter(ImageFilter.GaussianBlur(0.6))


def scan(source: Path, output: Path, seed: int) -> None:
    rng = random.Random(seed)  # noqa: S311 - reproducible pixels, not secrets
    original = pymupdf.open(source)
    scanned = pymupdf.open()
    for page in original:
        image = _scan_page(_render(page, SCAN_DPI), rng)
        jpeg = io.BytesIO()
        image.save(jpeg, "JPEG", quality=70)
        target = scanned.new_page(width=page.rect.width, height=page.rect.height)
        target.insert_image(target.rect, stream=jpeg.getvalue())
    scanned.save(output, garbage=4, deflate=True)


def _solve(matrix: list[list[float]], values: list[float]) -> list[float]:
    """Gaussian elimination with partial pivoting, for the eight perspective coefficients."""
    size = len(values)
    rows = [[*row, value] for row, value in zip(matrix, values, strict=True)]
    for col in range(size):
        pivot = max(range(col, size), key=lambda r: abs(rows[r][col]))
        rows[col], rows[pivot] = rows[pivot], rows[col]
        for r in range(size):
            if r != col:
                factor = rows[r][col] / rows[col][col]
                rows[r] = [a - factor * b for a, b in zip(rows[r], rows[col], strict=True)]
    return [rows[r][size] / rows[r][r] for r in range(size)]


def _perspective(photo: list[Point], paper: list[Point]) -> list[float]:
    """Coefficients mapping each point of the photo back to the paper, as Pillow expects."""
    matrix: list[list[float]] = []
    values: list[float] = []
    for (x, y), (u, v) in zip(photo, paper, strict=True):
        matrix.append([x, y, 1, 0, 0, 0, -x * u, -y * u])
        matrix.append([0, 0, 0, x, y, 1, -x * v, -y * v])
        values += [u, v]
    return _solve(matrix, values)


def _paper_corners(paper: tuple[int, int], rng: random.Random) -> list[Point]:
    """Where the page lands in the photo: a little tilted, the far edge narrower, never cut off."""
    width, height = PHOTO_SIZE
    page_height = height * 0.88
    page_width = page_height * paper[0] / paper[1]
    keystone = rng.uniform(25, 55)
    corners = [
        (-page_width / 2 + keystone, -page_height / 2),
        (page_width / 2 - keystone, -page_height / 2),
        (page_width / 2, page_height / 2),
        (-page_width / 2, page_height / 2),
    ]
    angle = math.radians(rng.uniform(-2.5, 2.5))
    cos, sin = math.cos(angle), math.sin(angle)
    return [
        (
            width / 2 + x * cos - y * sin + rng.uniform(-8, 8),
            height / 2 + x * sin + y * cos + rng.uniform(-8, 8),
        )
        for x, y in corners
    ]


def _lighting(rng: random.Random) -> Image.Image:
    """Light falling off across the page, and the soft shadow of the phone held over it."""
    # Rotated at full size and cropped from the middle: a square wider than the photo's diagonal
    # keeps the rotated corners out of frame, and nothing is enlarged into visible steps.
    side = math.ceil(math.hypot(*PHOTO_SIZE)) + 16
    light = Image.linear_gradient("L").resize((side, side), Image.Resampling.BICUBIC)
    light = light.rotate(rng.uniform(0, 360), Image.Resampling.BICUBIC)
    left, top = (side - PHOTO_SIZE[0]) // 2, (side - PHOTO_SIZE[1]) // 2
    light = light.crop((left, top, left + PHOTO_SIZE[0], top + PHOTO_SIZE[1]))
    light = light.point(lambda v: 200 + v * 55 // 255)
    shadow = Image.new("L", PHOTO_SIZE, 255)
    x, y = rng.uniform(0.2, 0.8) * PHOTO_SIZE[0], PHOTO_SIZE[1] * rng.uniform(0.75, 0.95)
    ImageDraw.Draw(shadow).ellipse((x - 500, y - 260, x + 500, y + 260), fill=215)
    return ImageChops.multiply(light, shadow.filter(ImageFilter.GaussianBlur(140)))


def photograph(source: Path, output: Path, seed: int) -> None:
    rng = random.Random(seed)  # noqa: S311 - reproducible pixels, not secrets
    original = pymupdf.open(source)
    if original.page_count != 1:
        pages = original.page_count
        raise ValueError(f"a photograph shows one page, and {source.name} has {pages}")
    paper = _render(original[0], 170)
    corners = _paper_corners(paper.size, rng)
    width, height = paper.size
    coefficients = _perspective(corners, [(0, 0), (width, 0), (width, height), (0, height)])

    desk = Image.new("RGB", PHOTO_SIZE, (96, 80, 66))
    photo = Image.blend(desk, _grain(PHOTO_SIZE, rng).convert("RGB"), 0.08)
    warp = (PHOTO_SIZE, Image.Transform.PERSPECTIVE, coefficients, Image.Resampling.BICUBIC)
    page = paper.transform(*warp)
    mask = Image.new("L", paper.size, 255).transform(*warp, fillcolor=0)
    photo.paste(page, (0, 0), mask)

    photo = ImageChops.multiply(photo, _lighting(rng).convert("RGB"))
    photo = photo.filter(ImageFilter.GaussianBlur(0.9))
    photo = Image.blend(photo, _grain(PHOTO_SIZE, rng).convert("RGB"), 0.04)
    photo.save(output, "JPEG", quality=82)
