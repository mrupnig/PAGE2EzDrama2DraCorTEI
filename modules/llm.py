from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path

import streamlit as st

from modules.paths import BASE_DIR

try:
    import openai as _openai
    _OPENAI_AVAILABLE = True
except ImportError:
    _OPENAI_AVAILABLE = False

_CACHE_DIR = Path.home() / "pagetodracor" / "llm_cache"
_TEMPLATES_DIR = Path.home() / "pagetodracor" / "prompt_templates"
_KEY_FILE = BASE_DIR / "secrets.toml"

# Empfohlene Modelle für OpenRouter (kostenlos/günstig)
RECOMMENDED_MODELS: list[str] = [
    "meta-llama/llama-3.1-8b-instruct:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "google/gemini-flash-1.5",
    "mistralai/mistral-7b-instruct",
    "google/gemini-2.0-flash-001",
]


def get_api_key() -> str | None:
    """Liest den OpenRouter-Key aus BASE_DIR/secrets.toml (App-Eingabe) oder
    aus st.secrets (klassischer .streamlit/secrets.toml-Weg, z. B. bei Deployment)."""
    if _KEY_FILE.exists():
        try:
            data = tomllib.loads(_KEY_FILE.read_text(encoding="utf-8"))
            key = data.get("OPENROUTER_API_KEY")
            if key:
                return key
        except (tomllib.TOMLDecodeError, OSError):
            pass
    try:
        return st.secrets.get("OPENROUTER_API_KEY")
    except Exception:
        return None


def save_api_key(key: str) -> None:
    """Speichert den OpenRouter-Key lokal unter BASE_DIR/secrets.toml (nie im Repo)."""
    _KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    _KEY_FILE.write_text(f'OPENROUTER_API_KEY = "{key}"\n', encoding="utf-8")
    _KEY_FILE.chmod(0o600)


def llm_available() -> bool:
    """True wenn openai-Paket installiert und API-Key vorhanden (App-Eingabe oder secrets.toml)."""
    if not _OPENAI_AVAILABLE:
        return False
    return bool(get_api_key())


def get_client() -> "_openai.OpenAI | None":
    if not llm_available():
        return None
    return _openai.OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=get_api_key(),
    )


def cached_call(
    messages: list[dict],
    model: str,
    cache_key: str,
    json_mode: bool = False,
) -> dict | None:
    """Schickt Anfrage an OpenRouter oder gibt gecachte Antwort zurück.

    Erwartet JSON-Antwort vom Modell. Gibt None zurück wenn LLM nicht
    verfügbar, die Antwort kein gültiges JSON ist oder ein Fehler auftritt.
    json_mode=True fordert vom Modell strikten JSON-Output an (nicht von
    jedem OpenRouter-Modell unterstützt — bei Fehlern greift der None-Fallback).
    Cache-Dateien: ~/pagetodracor/llm_cache/<sha256[:16]>.json
    """
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key_hash = hashlib.sha256(cache_key.encode()).hexdigest()[:16]
    cache_file = _CACHE_DIR / f"{key_hash}.json"

    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            cache_file.unlink(missing_ok=True)

    client = get_client()
    if client is None:
        return None

    try:
        kwargs = {"model": model, "messages": messages}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        response = client.chat.completions.create(**kwargs)
        raw = response.choices[0].message.content
        result = json.loads(raw)
        cache_file.write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return result
    except Exception:
        return None


def cache_stats() -> dict:
    """Gibt Anzahl und Gesamtgröße der gecachten Antworten zurück."""
    if not _CACHE_DIR.exists():
        return {"count": 0, "size_kb": 0}
    files = list(_CACHE_DIR.glob("*.json"))
    size = sum(f.stat().st_size for f in files)
    return {"count": len(files), "size_kb": round(size / 1024, 1)}


def clear_cache() -> int:
    """Löscht alle gecachten LLM-Antworten. Gibt Anzahl gelöschter Dateien zurück."""
    if not _CACHE_DIR.exists():
        return 0
    files = list(_CACHE_DIR.glob("*.json"))
    for f in files:
        f.unlink(missing_ok=True)
    return len(files)


def load_prompt_template(step_id: str, variant: str = "default") -> str:
    """Lädt ein Prompt-Template aus dem Templates-Verzeichnis."""
    _TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    template_file = _TEMPLATES_DIR / f"{step_id}_{variant}.txt"
    if template_file.exists():
        return template_file.read_text(encoding="utf-8")
    return ""


def save_prompt_template(step_id: str, variant: str, content: str) -> None:
    """Speichert ein Prompt-Template im Templates-Verzeichnis."""
    _TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    template_file = _TEMPLATES_DIR / f"{step_id}_{variant}.txt"
    template_file.write_text(content, encoding="utf-8")
