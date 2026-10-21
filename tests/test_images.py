"""The picture store (plan 1, P1-4 and P1-5). Includes acceptance test 15 (metadata removed)."""
import io

import pytest
from PIL import ExifTags, Image

from app.models.images import ImageError, ImageStore
from conftest import picture


@pytest.fixture
def store(tmp_path):
    return ImageStore(tmp_path / "uploads")


def test_a_jpeg_is_stored_as_pending_with_a_random_name(store):
    name = store.save_pending(io.BytesIO(picture()))
    assert len(name) == 36 and name.endswith(".jpg")
    assert (store.pending / name).is_file()


def test_png_with_transparency_becomes_a_jpeg_on_white(store):
    name = store.save_pending(io.BytesIO(picture("PNG", colour=(0, 0, 0, 0))))
    stored = Image.open(store.pending / name)
    assert stored.format == "JPEG" and stored.mode == "RGB"
    assert stored.getpixel((5, 5)) == (255, 255, 255)


def test_large_pictures_are_scaled_down(store):
    name = store.save_pending(io.BytesIO(picture(size=(3000, 2000))))
    assert Image.open(store.pending / name).size == (1200, 800)


def test_at15_gps_and_other_metadata_are_removed(store):
    exif = Image.Exif()
    exif[ExifTags.Base.Make] = "TestPhone"
    gps = exif.get_ifd(ExifTags.IFD.GPSInfo)
    gps[ExifTags.GPS.GPSLatitudeRef] = "N"
    gps[ExifTags.GPS.GPSLatitude] = (60.0, 23.0, 30.0)
    original = picture(exif=exif)
    assert Image.open(io.BytesIO(original)).getexif().get_ifd(ExifTags.IFD.GPSInfo), "test picture must carry GPS"
    stored = Image.open(store.pending / store.save_pending(io.BytesIO(original)))
    assert len(stored.getexif()) == 0 and "exif" not in stored.info


def test_the_phone_rotation_is_kept(store):
    exif = Image.Exif()
    exif[ExifTags.Base.Orientation] = 6          # "rotate 90 degrees", as phones write it
    name = store.save_pending(io.BytesIO(picture(size=(120, 80), exif=exif)))
    assert Image.open(store.pending / name).size == (80, 120)


@pytest.mark.parametrize("data, message", [
    (b"just some text, not a picture", "not a JPEG, PNG or WebP"),
    (picture("GIF"), "not a JPEG, PNG or WebP"),
    (b"\xff\xd8" + b"0" * (2 * 1024 * 1024), "larger than 2 MB"),
])
def test_at14_files_that_are_not_acceptable_pictures_are_refused(store, data, message):
    with pytest.raises(ImageError, match=message):
        store.save_pending(io.BytesIO(data))
    assert not store.pending.exists() or not any(store.pending.iterdir())


def test_at14_a_small_file_with_too_many_pixels_is_refused(store):
    buffer = io.BytesIO()
    Image.new("1", (7000, 6000)).save(buffer, "PNG")          # 42 megapixels in about 5 KB
    assert len(buffer.getvalue()) < 100_000
    with pytest.raises(ImageError, match="too many pixels"):
        store.save_pending(io.BytesIO(buffer.getvalue()))


def test_promote_moves_the_picture_into_place(store):
    name = store.save_pending(io.BytesIO(picture()))
    path = store.promote(name)
    assert path == f"uploads/{name}"
    assert (store.folder / name).is_file() and not (store.pending / name).exists()


def test_names_and_paths_from_outside_cannot_reach_other_files(store, tmp_path):
    secret = tmp_path / "secret.txt"
    secret.write_text("keep me")
    for bad in ("../secret.txt", "..", "", "pending/../../secret.txt"):
        with pytest.raises(ImageError):
            store.promote(bad)
        with pytest.raises(ImageError):
            store.discard_pending(bad)
    for bad in ("../secret.txt", "uploads/../secret.txt", "uploads/..", "/etc/passwd", None):
        store.delete(bad)
    assert secret.read_text() == "keep me"
