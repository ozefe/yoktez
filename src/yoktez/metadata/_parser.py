"""Pure JSON parser for the YOK NTC thesis metadata response body."""

from typing import TYPE_CHECKING

from yoktez.bilingual import Bilingual
from yoktez.metadata.models import Affiliation, References, ThesisMetadata

if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = ["parse_thesis_metadata"]

# `<strong>Label: </strong>` wraps the human-readable field name on `danisman`,
# `anahtarKelimeTr`, and `anahtarKelimeEn`. The wire shape is fixed: a single closing
# `</strong>` separates the label from the value, with no nested or trailing tags.
_STRONG_END = "</strong>"
_KEYWORD_SEP = ";"

_REF_KEYS = ("apa_ref", "ieee_ref", "mla_ref", "chicago_ref", "harvard_ref")


def parse_thesis_metadata(data: Mapping[str, str]) -> ThesisMetadata:
    """Map the flat metadata JSON object to a `ThesisMetadata`.

    Args:
        data: Deserialized JSON object as returned by YOK NTC. Missing keys are treated
            as absent fields.

    Returns:
        A populated `ThesisMetadata`. Each top-level field reduces to `None` when its
        source is missing or empty after prefix stripping.
    """
    supervisor = _strip_label(data.get("danisman", "")) or None
    affiliation = Affiliation.parse(data["yer"]) if data.get("yer") else None
    keywords = _parse_keywords(data.get("anahtarKelimeTr", ""))
    abstract_tr = data.get("trOzet") or None
    abstract_other = data.get("enOzet") or None
    references = _build_references(data)

    return ThesisMetadata(
        supervisor=supervisor,
        affiliation=affiliation,
        keywords=keywords,
        abstract_tr=abstract_tr,
        abstract_other=abstract_other,
        references=references,
    )


def _strip_label(value: str) -> str:
    return value.split(_STRONG_END, 1)[-1].strip()


def _parse_keywords(raw: str) -> list[Bilingual] | None:
    stripped = _strip_label(raw)
    if not stripped:
        return None

    keywords = [
        Bilingual.parse(chunk.strip())
        for chunk in stripped.split(_KEYWORD_SEP)
        if chunk.strip()
    ]
    return keywords or None


def _build_references(data: Mapping[str, str]) -> References | None:
    values = {key: data.get(key, "") for key in _REF_KEYS}
    if not any(values.values()):
        return None

    return References(
        apa=values["apa_ref"],
        ieee=values["ieee_ref"],
        mla=values["mla_ref"],
        chicago=values["chicago_ref"],
        harvard=values["harvard_ref"],
    )
