from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DrameContext:
    """Seitenübergreifender Zustand des Dramas während der PAGE-XML-Verarbeitung."""

    current_speaker: str | None = None
    current_act: str | None = None
    current_scene: str | None = None
    last_paragraph_incomplete: bool = False
    character_list: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "current_speaker": self.current_speaker,
            "current_act": self.current_act,
            "current_scene": self.current_scene,
            "last_paragraph_incomplete": self.last_paragraph_incomplete,
            "character_list": self.character_list,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DrameContext":
        return cls(
            current_speaker=data.get("current_speaker"),
            current_act=data.get("current_act"),
            current_scene=data.get("current_scene"),
            last_paragraph_incomplete=data.get("last_paragraph_incomplete", False),
            character_list=data.get("character_list", []),
        )
