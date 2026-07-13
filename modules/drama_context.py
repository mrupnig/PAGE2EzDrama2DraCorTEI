from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DramaContext:
    """Seitenübergreifender Zustand des Dramas während der KI-gestützten PAGE-XML-Verarbeitung."""

    current_speaker: str | None = None
    open_stage_direction: bool = False
    known_speakers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "current_speaker": self.current_speaker,
            "open_stage_direction": self.open_stage_direction,
            "known_speakers": self.known_speakers,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DramaContext":
        return cls(
            current_speaker=data.get("current_speaker"),
            open_stage_direction=data.get("open_stage_direction", False),
            known_speakers=data.get("known_speakers", []),
        )
