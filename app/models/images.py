"""Pictures of food items (plan 1, P1-4 and P1-5). Part of the model layer: it stores data, as files.

Flow: save_pending() -> the admin sees a preview -> promote() (Save) or discard_pending() (Discard).
Every upload is opened and re-saved by Pillow, so only real pictures are stored, hidden metadata (such as
GPS position) is removed, and file names are chosen by the server, never by the user.
"""
import io
import re
import secrets
import time
from pathlib import Path, PurePosixPath

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_BYTES = 2 * 1024 * 1024          # 2 MB
MAX_PIXELS = 40_000_000              # 40 megapixels: a small file can still be huge in memory
MAX_SIDE = 1200                      # stored pictures are at most 1200 x 1200 px
FORMATS = {"JPEG", "PNG", "WEBP"}
PENDING_MAX_AGE = 24 * 60 * 60       # pending uploads older than a day are cleaned up
NAME = re.compile(r"^[0-9a-f]{32}\.jpg$")


class ImageError(ValueError):
    """The upload is not acceptable; the message can be shown to the admin."""


class ImageStore:
    def __init__(self, folder):
        self.folder = Path(folder)               # the uploads folder; paths are stored as "uploads/<name>"
        self.pending = self.folder / "pending"

    def save_pending(self, stream):
        """Check and re-save an uploaded picture as a pending file. Returns its name."""
        data = stream.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ImageError("The picture is larger than 2 MB.")
        try:
            with Image.open(io.BytesIO(data)) as probe:
                kind, (width, height) = probe.format, probe.size
                probe.verify()                   # checks the file structure without decoding all pixels
        except Image.DecompressionBombError:
            raise ImageError("The picture has too many pixels (more than 40 megapixels).")
        except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
            raise ImageError("The file is not a JPEG, PNG or WebP picture.")
        if kind not in FORMATS:
            raise ImageError("The file is not a JPEG, PNG or WebP picture.")
        if width * height > MAX_PIXELS:
            raise ImageError("The picture has too many pixels (more than 40 megapixels).")

        with Image.open(io.BytesIO(data)) as original:
            picture = ImageOps.exif_transpose(original)          # keep the phone's rotation ...
            picture = _on_white(picture)                         # ... then drop all metadata on save
            picture.thumbnail((MAX_SIDE, MAX_SIDE))
            name = secrets.token_hex(16) + ".jpg"
            self.pending.mkdir(parents=True, exist_ok=True)
            picture.save(self.pending / name, "JPEG", quality=85)
        self._remove_old_pending()
        return name

    def promote(self, name):
        """Save: move a pending picture into place. Returns the path to store on the food item."""
        source = self._pending_file(name)
        if not source.is_file():
            raise ImageError("The preview has expired. Please upload the picture again.")
        source.replace(self.folder / name)
        return f"uploads/{name}"

    def discard_pending(self, name):
        self._pending_file(name).unlink(missing_ok=True)

    def delete(self, image_path):
        """Delete a stored picture, but only a file directly inside the uploads folder."""
        relative = PurePosixPath(image_path or "")
        if relative.parent != PurePosixPath("uploads") or relative.name in ("", ".", ".."):
            return
        (self.folder / relative.name).unlink(missing_ok=True)

    @staticmethod
    def pending_path(name):
        return f"uploads/pending/{name}"

    def _pending_file(self, name):
        if not NAME.match(name or ""):
            raise ImageError("Unknown picture.")
        return self.pending / name

    def _remove_old_pending(self):
        limit = time.time() - PENDING_MAX_AGE
        for file in self.pending.glob("*.jpg"):
            if file.stat().st_mtime < limit:
                file.unlink(missing_ok=True)


def _on_white(picture):
    """JPEG has no transparency: put transparent pictures on a white background."""
    if picture.mode in ("RGBA", "LA") or (picture.mode == "P" and "transparency" in picture.info):
        rgba = picture.convert("RGBA")
        background = Image.new("RGB", rgba.size, "white")
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return picture.convert("RGB")
