"""Enums for YOK NTC filter values."""

from enum import Enum, IntEnum, StrEnum
from typing import Self, overload

__all__ = [
    "AccessType",
    "AdvancedOperator",
    "AssetStatus",
    "KeywordGroup",
    "KeywordLanguage",
    "MatchType",
    "SearchField",
    "ThesisLanguage",
    "ThesisStatus",
    "ThesisType",
    "UniversitySource",
    "coerce",
]


# Integer enums
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=


class ThesisType(IntEnum):
    """Academic degree level."""

    ALL = 0
    MASTER = 1
    DOCTORATE = 2
    SPECIALIZATION_IN_MEDICINE = 3
    PROFICIENCY_IN_ART = 4
    SPECIALIZATION_IN_DENTISTRY = 5
    MINOR_SPECIALIZATION_IN_MEDICINE = 6
    EXPERTISE_IN_PHARMACY = 7

    @classmethod
    def from_display(cls, name: str) -> Self:
        """Resolve a Turkish wire-form display name to a `ThesisType` member.

        `name` is the value found in YOK NTC responses (Turkish only). `from_display`
        never emits `ALL` -- that sentinel is request-side only.

        Raises:
            ValueError: `name` is not a known Turkish display string.
        """
        try:
            return _THESIS_TYPE_BY_DISPLAY[name]  # pyright: ignore[reportReturnType]
        except KeyError as exc:
            msg = f"{name!r} is not a ThesisType display name"
            raise ValueError(msg) from exc


class ThesisStatus(IntEnum):
    """Lifecycle status of a thesis.

    Note:
        Code `2` is undocumented, thus omitted from this enum. Callers needing it may
        pass raw int `2` through `coerce`.
    """

    ALL = 0
    PREPARING = 1
    APPROVED = 3


class ThesisLanguage(IntEnum):
    """Language of a thesis.

    Note:
        Codes 22-25, 38, and 40 are gaps in the YOK NTC namespace per and are not
        represented here.
    """

    ALL = 0
    TURKISH = 1
    ENGLISH = 2
    ARABIC = 3
    GERMAN = 4
    FRENCH = 5
    SPANISH = 6
    ITALIAN = 7
    RUSSIAN = 8
    POLISH = 9
    CHINESE = 10
    KURDISH = 11
    AZERBAIJANI = 12
    BULGARIAN = 13
    CZECH = 14
    ROMANIAN = 15
    DUTCH = 16
    JAPANESE = 17
    PERSIAN = 18
    GREEK = 19
    SLOVENIAN = 20
    MACEDONIAN = 21
    # 22-25: Gap
    ADYGHE = 26
    KYRGYZ = 27
    BOSNIAN = 28
    GEORGIAN = 29
    KOREAN = 30
    ARMENIAN = 31
    ZAZAKI = 32
    MALAY = 33
    KAZAKH = 34
    UKRAINIAN = 35
    MONGOLIAN = 36
    INDONESIAN = 37
    # 38: Gap
    UZBEK = 39
    # 40: Gap
    HUNGARIAN = 41
    SERBIAN = 42
    PORTUGUESE = 43
    ALBANIAN = 44
    LATVIAN = 45
    NORWEGIAN = 46

    @classmethod
    def from_display(cls, name: str) -> Self:
        """Resolve a Turkish wire-form language name to a `ThesisLanguage` member.

        `name` is the value found in YOK NTC responses (Turkish only). The map covers
        the known languages; unmapped names raise `ValueError` so the parser layer can
        wrap it as `ParseError` and surface the missing entry. `from_display` never
        emits `ALL` -- that sentinel is request-side only.

        Raises:
            ValueError: `name` is not a known Turkish language display string.
        """
        try:
            return _THESIS_LANGUAGE_BY_DISPLAY[name]  # pyright: ignore[reportReturnType]
        except KeyError as exc:
            msg = f"{name!r} is not a ThesisLanguage display name"
            raise ValueError(msg) from exc


class SearchField(IntEnum):
    """Field selector for searches."""

    THESIS_NAME = 1
    AUTHOR = 2
    SUPERVISOR = 3
    SUBJECT = 4
    KEYWORD = 5
    ABSTRACT = 6
    ALL = 7


class AccessType(IntEnum):
    """Full-text access status."""

    ALL = 0
    AUTHORIZED = 1
    UNAUTHORIZED = 2


class MatchType(IntEnum):
    """Match mode for advanced search."""

    EXACT = 1
    INCLUDES = 2


class KeywordLanguage(IntEnum):
    """Language filter for keyword search."""

    ALL = 0
    TURKISH = 1
    ENGLISH = 2


class AssetStatus(IntEnum):
    """Classification of a thesis-assets response."""

    AVAILABLE = 1
    UNDER_EMBARGO = 2
    NO_PERMIT = 3
    PREPARING = 4


# String enums
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=


class AdvancedOperator(StrEnum):
    """Boolean operator joining advanced-search terms."""

    AND = "and"
    OR = "or"
    NOT = "not"


class UniversitySource(StrEnum):
    """Origin filter for `GetUniversities`."""

    TR = "TR"
    INT = "INT"


class KeywordGroup(StrEnum):
    """Academical group of keywords."""

    SCIENCE = "F"
    SOCIAL_SCIENCES = "S"
    MEDICINE = "T"


# Helpers
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=


@overload
def coerce[E: IntEnum](enum_cls: type[E], value: E | int | str) -> int: ...
@overload
def coerce[E: StrEnum](enum_cls: type[E], value: E | str) -> str: ...
def coerce(enum_cls: type[Enum], value: object) -> int | str:
    """Resolve `value` to its YOK NTC wire-format representation.

    Behavior:
        - If `value` is an instance of `enum_cls`, return its `.value`.
        - For `IntEnum` subclasses: accept `int` or digit-string and either map to a
          known member's value or pass the int through unchanged (tolerates new YOK NTC
          codes not yet enumerated here). Member names are accepted as well.
        - For `StrEnum` subclasses: accept the member name or the wire string. Unknown
          strings raise `ValueError`. Typos in small enum sets like `KeywordGroup` must
          fail loudly rather than silently producing broken requests.

    Raises:
        TypeError: `value` is not an `Enum`, `int`, or `str`.
        ValueError: `value` cannot be mapped to a member and passthrough does not apply.
    """
    if isinstance(value, enum_cls):
        return value.value

    if issubclass(enum_cls, IntEnum):
        return coerce_int_enum(enum_cls, value)

    if issubclass(enum_cls, StrEnum):
        return coerce_str_enum(enum_cls, value)

    msg = f"Unsupported enum class: {enum_cls!r}"
    raise TypeError(msg)


def coerce_int_enum(enum_cls: type[IntEnum], value: object) -> int:
    if isinstance(value, int):
        return value  # known or unknown int; let YOK NTC adjudicate

    if isinstance(value, str):
        if value in enum_cls.__members__:
            return enum_cls[value].value

        try:
            return int(value)
        except ValueError as exc:
            msg = (
                f"{value!r} is not a member name or numeric value of "
                f"{enum_cls.__name__}"
            )
            raise ValueError(msg) from exc

    msg = f"Cannot coerce {type(value).__name__} to {enum_cls.__name__}"
    raise TypeError(msg)


def coerce_str_enum(enum_cls: type[StrEnum], value: object) -> str:
    if isinstance(value, str):
        if value in enum_cls.__members__:
            return enum_cls[value].value

        try:
            return enum_cls(value).value
        except ValueError as exc:
            msg = f"{value!r} is not a member of {enum_cls.__name__}"
            raise ValueError(msg) from exc

    msg = f"Cannot coerce {type(value).__name__} to {enum_cls.__name__}"
    raise TypeError(msg)


# Response-side display-name lookup tables
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# Sourced from real YOK NTC search-result HTML. Turkish keys only. `ALL` is
# intentionally absent: it's a filter-only sentinel that never appears in wire-side
# responses.


_THESIS_TYPE_BY_DISPLAY: dict[str, ThesisType] = {
    "Yüksek Lisans": ThesisType.MASTER,
    "Doktora": ThesisType.DOCTORATE,
    "Tıpta Uzmanlık": ThesisType.SPECIALIZATION_IN_MEDICINE,
    "Sanatta Yeterlik": ThesisType.PROFICIENCY_IN_ART,
    "Diş Hekimliği Uzmanlık": ThesisType.SPECIALIZATION_IN_DENTISTRY,
    "Tıpta Yan Dal Uzmanlık": ThesisType.MINOR_SPECIALIZATION_IN_MEDICINE,
    "Eczacılıkta Uzmanlık": ThesisType.EXPERTISE_IN_PHARMACY,
}

_THESIS_LANGUAGE_BY_DISPLAY: dict[str, ThesisLanguage] = {
    "Türkçe": ThesisLanguage.TURKISH,
    "İngilizce": ThesisLanguage.ENGLISH,
    "Arapça": ThesisLanguage.ARABIC,
    "Almanca": ThesisLanguage.GERMAN,
    "Fransızca": ThesisLanguage.FRENCH,
    "İspanyolca": ThesisLanguage.SPANISH,
    "İtalyanca": ThesisLanguage.ITALIAN,
    "Rusça": ThesisLanguage.RUSSIAN,
    "Lehçe": ThesisLanguage.POLISH,
    "Çince": ThesisLanguage.CHINESE,
    "Kürtçe": ThesisLanguage.KURDISH,
    "Azerice": ThesisLanguage.AZERBAIJANI,
    "Bulgarca": ThesisLanguage.BULGARIAN,
    "Çekçe": ThesisLanguage.CZECH,
    "Romence": ThesisLanguage.ROMANIAN,
    "Felemenkçe": ThesisLanguage.DUTCH,
    "Japonca": ThesisLanguage.JAPANESE,
    "Farsça": ThesisLanguage.PERSIAN,
    "Yunanca": ThesisLanguage.GREEK,
    "Slovence": ThesisLanguage.SLOVENIAN,
    "Makedonca": ThesisLanguage.MACEDONIAN,
    "Çerkezce": ThesisLanguage.ADYGHE,
    "Kırgızca": ThesisLanguage.KYRGYZ,
    "Boşnakça": ThesisLanguage.BOSNIAN,
    "Gürcüce": ThesisLanguage.GEORGIAN,
    "Korece": ThesisLanguage.KOREAN,
    "Ermenice": ThesisLanguage.ARMENIAN,
    "Zazaca": ThesisLanguage.ZAZAKI,
    "Malayca": ThesisLanguage.MALAY,
    "Kazakça": ThesisLanguage.KAZAKH,
    "Ukraynaca": ThesisLanguage.UKRAINIAN,
    "Moğolca": ThesisLanguage.MONGOLIAN,
    "Endonezce": ThesisLanguage.INDONESIAN,
    "Özbekçe": ThesisLanguage.UZBEK,
    "Macarca": ThesisLanguage.HUNGARIAN,
    "Sırpça": ThesisLanguage.SERBIAN,
    "Portekizce": ThesisLanguage.PORTUGUESE,
    "Arnavutça": ThesisLanguage.ALBANIAN,
    "Letonca": ThesisLanguage.LATVIAN,
    "Norveççe": ThesisLanguage.NORWEGIAN,
}
