from pathlib import Path
import os

BASE_DIR = Path(os.environ.get("PAGETODRACOR_HOME", Path.home() / "pagetodracor"))


def get_step_paths(project_dir: Path) -> dict[str, Path]:
    work = project_dir / "work" / "current"
    return {
        "source": project_dir / "source",
        "step1":  work / "step1_ezdrama.txt",
        "step2":  work / "step2_speakers_fixed.txt",
        "step3":  work / "step3_brackets_fixed.txt",
        "step4":  work / "step4_normalized.txt",
        "step5":  work / "step5_cleaned.txt",
        "step6":  work / "step6_tei.xml",
    }
