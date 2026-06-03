import shutil
import subprocess
from pathlib import Path

_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}


def kraken_available() -> bool:
    return shutil.which("kraken") is not None


def calamari_available() -> bool:
    return shutil.which("calamari-predict") is not None


def get_kraken_version() -> str | None:
    if not kraken_available():
        return None
    result = subprocess.run(["kraken", "--version"], capture_output=True, text=True)
    return (result.stdout.strip() or result.stderr.strip()) or None


def get_calamari_version() -> str | None:
    if not calamari_available():
        return None
    result = subprocess.run(
        ["calamari-predict", "--version"], capture_output=True, text=True
    )
    return (result.stdout.strip() or result.stderr.strip()) or None


def run_kraken_binarize_segment(
    image_path: Path,
    output_xml: Path,
    segment_model: Path | None = None,
) -> subprocess.CompletedProcess:
    """Binarisiert und segmentiert ein Bild mit Kraken.

    segment_model=None → eingebautes blla-Standardmodell.
    returncode != 0 bei Fehler; stderr enthält den Kraken-Log.
    """
    cmd = [
        "kraken",
        "-i", str(image_path),
        str(output_xml),
        "binarize",
        "segment", "-bl",
    ]
    if segment_model is not None:
        cmd += ["-m", str(segment_model)]
    return subprocess.run(cmd, capture_output=True, text=True)


def run_calamari_predict(
    page_xml_path: Path,
    checkpoint_path: Path,
) -> subprocess.CompletedProcess:
    """Führt Calamari-Texterkennung auf einem PAGE-XML durch.

    Modifiziert die Datei in-place: jede TextLine bekommt ein TextEquiv-Element.
    returncode != 0 bei Fehler.
    """
    cmd = [
        "calamari-predict",
        "--checkpoint", str(checkpoint_path),
        "--files", str(page_xml_path),
    ]
    return subprocess.run(cmd, capture_output=True, text=True)


def get_available_kraken_models(model_dir: Path) -> list[Path]:
    if not model_dir.exists():
        return []
    return sorted(model_dir.glob("*.mlmodel"))


def get_available_calamari_checkpoints(model_dir: Path) -> list[Path]:
    """Findet Calamari-Checkpoints: Ordner mit *.ckpt.json oder einzelne .ckpt.json-Dateien."""
    if not model_dir.exists():
        return []
    checkpoints: list[Path] = []
    for item in model_dir.iterdir():
        if item.is_dir() and any(item.glob("*.ckpt.json")):
            checkpoints.append(item)
        elif item.suffix == ".json" and "ckpt" in item.name:
            checkpoints.append(item)
    return sorted(checkpoints)


def list_image_files(images_dir: Path) -> list[Path]:
    if not images_dir.exists():
        return []
    return sorted(
        p for p in images_dir.iterdir()
        if p.suffix.lower() in _IMAGE_SUFFIXES
    )
