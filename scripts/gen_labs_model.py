"""Генерирует common/labs_model.py (статический класс Labs) из реестра
common/labs.py. Запуск из корня проекта:  python -m scripts.gen_labs_model
Тест test_labs_model_in_sync следит, что файл не отстал от реестра."""
from pathlib import Path

from common.labs import LAB_SPECS, REQUIRED_LABS

TARGET = Path(__file__).resolve().parents[1] / "common" / "labs_model.py"

HEADER = '''\
# AUTO-GENERATED: python -m scripts.gen_labs_model. Не править вручную —
# менять показатели нужно в common/labs.py и перегенерировать файл.
from pydantic import BaseModel, ConfigDict, Field


class Labs(BaseModel):
    """Числовая матрица показателей (одна строка = один пациент)."""
    model_config = ConfigDict(extra="forbid")

'''


def render() -> str:
    lines = []
    for name, s in LAB_SPECS.items():
        desc = f"{s.desc}, {s.unit}"
        bounds = f"ge={s.lo!r}, le={s.hi!r}, allow_inf_nan=False, description={desc!r}"
        if name in REQUIRED_LABS:
            lines.append(f"    {name}: float = Field({bounds})")
        else:
            lines.append(f"    {name}: float | None = Field(None, {bounds})")
    return HEADER + "\n".join(lines) + "\n"


if __name__ == "__main__":
    TARGET.write_text(render(), encoding="utf-8")
    print("written", TARGET)
