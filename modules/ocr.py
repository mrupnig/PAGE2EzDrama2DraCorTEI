import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

_PAGE_NS = "http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15"
_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}


def _find_tool(name: str) -> str | None:
    """Sucht ein CLI-Tool im venv-bin oder im System-PATH.

    Prüft zuerst das bin-Verzeichnis des aktiven Python-Interpreters,
    dann den System-PATH. Das ist nötig, weil Streamlit aus dem venv läuft,
    der System-PATH das venv aber nicht kennt.
    """
    venv_bin = Path(sys.executable).parent
    candidate = venv_bin / name
    if candidate.is_file():
        return str(candidate)
    return shutil.which(name)


def kraken_available() -> bool:
    return _find_tool("kraken") is not None


def calamari_available() -> bool:
    return _find_tool("calamari-predict") is not None


def get_kraken_version() -> str | None:
    tool = _find_tool("kraken")
    if not tool:
        return None
    result = subprocess.run([tool, "--version"], capture_output=True, text=True)
    return (result.stdout.strip() or result.stderr.strip()) or None


def get_calamari_version() -> str | None:
    tool = _find_tool("calamari-predict")
    if not tool:
        return None
    result = subprocess.run([tool, "--version"], capture_output=True, text=True)
    return (result.stdout.strip() or result.stderr.strip()) or None


def run_kraken_binarize(
    image_path: Path,
    output_path: Path,
) -> subprocess.CompletedProcess:
    """Binarisiert ein Bild mit Kraken 7.x (Graustufen/Otsu).

    Kraken 7.x-Syntax:
        kraken --device cpu -i INPUT OUTPUT binarize
    """
    tool = _find_tool("kraken") or "kraken"
    cmd = [
        tool,
        "--device", "cpu",
        "-i", str(image_path), str(output_path),
        "binarize",
    ]
    return subprocess.run(cmd, capture_output=True, text=True)


def run_kraken_segment(
    image_path: Path,
    output_xml: Path,
    segment_model: Path | None = None,
) -> subprocess.CompletedProcess:
    """Segmentiert ein (binarisiertes) Bild mit Kraken 7.x.

    Erzeugt eine PAGE-XML mit Regionen, Baselines und Zeilensegmenten —
    ohne Text. imageFilename zeigt auf image_path (das binarisierte Bild).
    segment_model=None → eingebautes blla-Standardmodell.

    Kraken 7.x-Syntax:
        kraken -x --device cpu -i INPUT OUTPUT segment -bl [--model MODEL]
    """
    tool = _find_tool("kraken") or "kraken"
    cmd = [
        tool,
        "-x",           # PAGE-XML-Ausgabe (statt Standard-JSON)
        "--device", "cpu",
        "-i", str(image_path), str(output_xml),
        "segment", "-bl",
    ]
    if segment_model is not None:
        # --model (Langform) statt -i (Kurzform) um Konflikt mit globalem -i zu vermeiden
        cmd += ["--model", str(segment_model)]
    return subprocess.run(cmd, capture_output=True, text=True)


def run_calamari_predict(
    page_xml_path: Path,
    checkpoint_path: Path,
) -> subprocess.CompletedProcess:
    """Führt Calamari 1.x Texterkennung auf einem PAGE-XML durch.

    Liest Zeilensegmente aus dem PAGE-XML und schreibt den erkannten
    Text als TextEquiv-Elemente zurück.

    Calamari 1.x erwartet den Checkpoint-Pfad OHNE .json-Extension.
    Der Dateiname im Dateisystem ist z.B. model.ckpt.json — übergeben
    wird model.ckpt (also ohne abschließendes .json).

    Calamari 1.x-Syntax:
        calamari-predict --dataset PAGEXML --files PAGE.xml --checkpoint MODEL.ckpt
    """
    tool = _find_tool("calamari-predict") or "calamari-predict"

    # .json-Extension entfernen falls der Nutzer den vollen Pfad angegeben hat
    checkpoint_str = str(checkpoint_path)
    if checkpoint_str.endswith(".json"):
        checkpoint_str = checkpoint_str[:-5]

    cmd = [
        tool,
        "--dataset", "PAGEXML",
        "--files", str(page_xml_path),
        "--checkpoint", checkpoint_str,
    ]
    return subprocess.run(cmd, capture_output=True, text=True)


def fix_page_xml_image_path(page_xml_path: Path, original_image: Path) -> None:
    """Korrigiert den imageFilename-Pfad in der PAGE-XML nach der Kraken-Segmentierung.

    Kraken 7.x schreibt den Pfad zur temporären binarisierten Datei in imageFilename.
    Diese Datei wird nach dem Prozess gelöscht. Diese Funktion setzt stattdessen
    den Pfad zum Original-Bild, damit Calamari die Zeilen korrekt extrahieren kann.
    """
    ET.register_namespace("", _PAGE_NS)
    tree = ET.parse(page_xml_path)
    root = tree.getroot()

    page = root.find(f"{{{_PAGE_NS}}}Page")
    if page is not None:
        page.set("imageFilename", str(original_image.resolve()))

    tree.write(str(page_xml_path), encoding="unicode", xml_declaration=True)


def get_available_kraken_models(model_dir: Path) -> list[Path]:
    """Gibt alle .mlmodel-Dateien im Modellverzeichnis zurück."""
    if not model_dir.exists():
        return []
    return sorted(model_dir.glob("*.mlmodel"))


def get_available_calamari_checkpoints(model_dir: Path) -> list[Path]:
    """Findet Calamari-1.x-Checkpoints im Modellverzeichnis.

    Sucht rekursiv nach *.ckpt.json-Dateien und gibt den Pfad
    OHNE .json-Extension zurück (Calamari-Konvention für --checkpoint).
    """
    if not model_dir.exists():
        return []
    checkpoints: list[Path] = []
    for f in model_dir.rglob("*.ckpt.json"):
        checkpoints.append(f.with_suffix(""))  # /pfad/model.ckpt (ohne .json)
    return sorted(checkpoints)


def list_image_files(images_dir: Path) -> list[Path]:
    """Gibt alle Bilddateien im Verzeichnis zurück, sortiert nach Dateiname."""
    if not images_dir.exists():
        return []
    return sorted(
        p for p in images_dir.iterdir()
        if p.suffix.lower() in _IMAGE_SUFFIXES
    )
