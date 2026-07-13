import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Literal

from modules.paths import BASE_DIR, get_step_paths

STEP_KEYS = ["step0", "step1", "step2", "step3", "step4", "step5", "step6"]

_UMLAUT_MAP = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
                              "Ä": "ae", "Ö": "oe", "Ü": "ue"})


def slugify(name: str) -> str:
    name = name.translate(_UMLAUT_MAP)
    name = name.lower()
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"[\s-]+", "_", name)
    return name.strip("_") or "projekt"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _default_step() -> dict:
    return {
        "status": "pending",
        "mode": "review",
        "completed_at": None,
        "output_file": None,
        "state": {},
    }


def _skipped_step() -> dict:
    return {
        "status": "skipped",
        "mode": "review",
        "completed_at": None,
        "output_file": None,
        "state": {},
    }


class Project:
    def __init__(self, project_dir: Path, data: dict) -> None:
        self.project_dir = project_dir
        self._data = data

    # ── Factory methods ───────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        name: str,
        is_prose: bool,
        bracketstages: bool,
        input_type: Literal["page_xml", "images"] = "page_xml",
        llm_mode: Literal["manual", "assisted"] = "manual",
    ) -> "Project":
        slug = slugify(name)
        project_dir = BASE_DIR / "projects" / slug
        if project_dir.exists():
            raise ValueError(f"Projekt '{slug}' existiert bereits.")

        if input_type == "images":
            (project_dir / "source" / "images").mkdir(parents=True)
            (project_dir / "source" / "page").mkdir(parents=True)
        else:
            (project_dir / "source").mkdir(parents=True)

        (project_dir / "work" / "current").mkdir(parents=True)
        (project_dir / "work" / "history").mkdir(parents=True)

        now = _now()
        data: dict = {
            "name": name,
            "slug": slug,
            "created": now,
            "modified": now,
            "settings": {
                "is_prose": is_prose,
                "bracketstages": bracketstages,
                "input_type": input_type,
                "llm_mode": llm_mode,
                "preprocessing_mode": "guided",
                "ocr": {
                    "kraken_segment_model": None,
                    "calamari_checkpoint": None,
                },
                "llm": {
                    "model_step1": "nvidia/nemotron-nano-9b-v2:free",
                    "model_step2": "nvidia/nemotron-nano-9b-v2:free",
                    "model_step3": "google/gemini-3.1-flash-lite",
                    "model_step4": "nvidia/nemotron-nano-9b-v2:free",
                    "model_step1_auto": "google/gemini-3.5-flash",
                },
            },
            "metadata": {
                "title": "", "subtitle": "", "author": "",
                "language": "de", "dracor_id": "",
                "source_url": "", "source_institution": "",
                "wikidata_id": "", "year_written": "",
                "year_premiere": "", "year_print": "",
            },
            "steps": {
                "step0": _default_step() if input_type == "images" else _skipped_step(),
                "step1": _default_step(),
                "step2": _default_step(),
                "step3": _default_step(),
                "step4": _default_step(),
                "step5": _default_step(),
                "step6": _default_step(),
            },
        }
        p = cls(project_dir, data)
        p._write()
        return p

    @classmethod
    def load(cls, project_dir: Path) -> "Project":
        data = json.loads((project_dir / "project.json").read_text(encoding="utf-8"))
        return cls(project_dir, data)

    @classmethod
    def list_all(cls) -> list["Project"]:
        projects_dir = BASE_DIR / "projects"
        if not projects_dir.exists():
            return []
        return [
            cls.load(d)
            for d in sorted(projects_dir.iterdir())
            if d.is_dir() and (d / "project.json").exists()
        ]

    # ── Properties ───────────────────────────────────────────────────────────

    @property
    def name(self) -> str:
        return self._data["name"]

    @property
    def slug(self) -> str:
        return self._data["slug"]

    @property
    def settings(self) -> dict:
        return self._data["settings"]

    @property
    def metadata(self) -> dict:
        return self._data["metadata"]

    @property
    def modified(self) -> str:
        return self._data["modified"]

    # ── Step management ───────────────────────────────────────────────────────

    def get_step(self, key: str) -> dict:
        # Fallback für ältere Projekte ohne step0
        return self._data["steps"].get(key, _skipped_step())

    def save_step(self, key: str, output_file: Path, state: dict) -> None:
        """Versioniert bestehende Ausgabe in history, schreibt neuen Step-Status."""
        paths = get_step_paths(self.project_dir)
        current = paths[key]

        if current.exists() and current.is_file():
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            history_path = (
                self.project_dir / "work" / "history"
                / f"{key}_{ts}{current.suffix}"
            )
            shutil.copy2(current, history_path)

        step = self._data["steps"].setdefault(key, _default_step())
        step["status"] = "done"
        step["completed_at"] = _now()
        step["output_file"] = str(output_file.relative_to(self.project_dir))
        step["state"] = state

        idx = STEP_KEYS.index(key)
        for downstream in STEP_KEYS[idx + 1:]:
            if self._data["steps"].get(downstream, {}).get("status") == "done":
                self._data["steps"][downstream]["status"] = "stale"

        self._touch()
        self._write()

    def update_step_state(self, key: str, state: dict) -> None:
        """Persistiert Zwischenzustand ohne den Step als done zu markieren."""
        self._data["steps"].setdefault(key, _default_step())["state"].update(state)
        self._touch()
        self._write()

    def save_settings(self, settings: dict) -> None:
        self._data["settings"].update(settings)
        self._touch()
        self._write()

    def save_metadata(self, metadata: dict) -> None:
        self._data["metadata"].update(metadata)
        self._touch()
        self._write()

    # ── History / rollback ───────────────────────────────────────────────────

    def get_history(self, key: str) -> list[Path]:
        history_dir = self.project_dir / "work" / "history"
        return sorted(history_dir.glob(f"{key}_*"), reverse=True)

    def rollback(self, key: str, history_file: Path) -> None:
        paths = get_step_paths(self.project_dir)
        shutil.copy2(history_file, paths[key])

        step = self._data["steps"].setdefault(key, _default_step())
        step["status"] = "done"
        step["completed_at"] = _now()

        idx = STEP_KEYS.index(key)
        for downstream in STEP_KEYS[idx + 1:]:
            if self._data["steps"].get(downstream, {}).get("status") == "done":
                self._data["steps"][downstream]["status"] = "stale"

        self._touch()
        self._write()

    # ── Navigation helper ────────────────────────────────────────────────────

    def first_pending_step(self) -> str:
        """Gibt den Key des ersten nicht abgeschlossenen und nicht übersprungenen Steps zurück."""
        for key in STEP_KEYS:
            status = self._data["steps"].get(key, {}).get("status", "pending")
            if status not in ("done", "skipped"):
                return key
        return STEP_KEYS[-1]

    # ── Internal ─────────────────────────────────────────────────────────────

    def _touch(self) -> None:
        self._data["modified"] = _now()

    def _write(self) -> None:
        (self.project_dir / "project.json").write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
