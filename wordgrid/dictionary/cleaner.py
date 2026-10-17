import re
from typing import Set, Dict, Tuple, Optional
from pathlib import Path

# Irregular plural mapping: plural -> singular
IRREGULAR_PLURAL_MAP: Dict[str, str] = {
    "MICE": "MOUSE",
    "TEETH": "TOOTH",
    "FEET": "FOOT",
    "MEN": "MAN",
    "WOMEN": "WOMAN",
    "CHILDREN": "CHILD",
    "GEESE": "GOOSE",
    "OXEN": "OX",
    "CACTI": "CACTUS",
    "FUNGI": "FUNGUS",
    "NUCLEI": "NUCLEUS",
    "SYLLABI": "SYLLABUS",
    "CRISES": "CRISIS",
    "ANALYSES": "ANALYSIS",
    "THESES": "THESIS",
    "OASES": "OASIS",
    "DIAGNOSES": "DIAGNOSIS",
    "HYPOTHESES": "HYPOTHESIS",
    "PARENTHESES": "PARENTHESIS",
    "PROGNOSES": "PROGNOSIS",
    "SYNOPSES": "SYNOPSIS",
    "AXES": "AXIS",
    "BACTERIA": "BACTERIUM",
    "DATA": "DATUM",
    "CURRICULA": "CURRICULUM",
    "MEMORANDA": "MEMORANDUM",
    "PHENOMENA": "PHENOMENON",
    "CRITERIA": "CRITERION",
    "LARVAE": "LARVA",
    "ALUMNAE": "ALUMNA",
    "ALUMNI": "ALUMNUS",
    "FOCI": "FOCUS",
    "RADII": "RADIUS",
    "VERTICES": "VERTEX",
    "INDICES": "INDEX",
    "MATRICES": "MATRIX",
    "APPENDICES": "APPENDIX",
}

# Curated list of known valid singular English words ending in 'S' that MUST NEVER be excluded as plurals.
PRESERVED_SINGULARS: Set[str] = {
    # Common short words
    "BUS", "GAS", "LENS", "YES", "THIS", "THUS", "PLUS", "MINUS",
    # Latin / Greek root singulars
    "ANALYSIS", "BASIS", "CRISIS", "AXIS", "CHAOS", "ATLAS", "CITRUS", "STATUS",
    "APPARATUS", "SPECIES", "SERIES", "OASIS", "THESIS", "GENESIS", "DIAGNOSIS",
    "PROGNOSIS", "SYNOPSIS", "METAMORPHOSIS", "PARALYSIS", "NEUROSIS", "PSYCHOSIS",
    "SCLEROSIS", "THROMBOSIS", "TUBERCULOSIS", "PSORIASIS", "SYPHILIS", "PROBOSCIS",
    "IBIS", "MANTIS", "PELVIS", "CLITORIS", "EPIGLOTTIS", "TRELLIS", "PORTCULLIS",
    "MARQUIS", "AMARYLLIS", "GLADIOLUS", "CROCUS", "NARCISSUS", "HIBISCUS", "FICUS",
    "COLEUS", "ASPARAGUS", "EUCALYPTUS", "LOTUS", "PAPYRUS", "ANUS", "SINUS", "UTERUS",
    "FETUS", "MUCUS", "TYPHUS", "TETANUS", "CHOLERA", "RABIES", "SCABIES", "MEASLES",
    "MUMPS", "RICKETS", "SHINGLES", "FOCUS", "VIRUS", "CAMPUS", "CIRCUS", "GENIUS",
    "RADIUS", "BONUS", "WALRUS", "CACTUS", "FUNGUS", "HIPPOPOTAMUS", "PLATYPUS",
    "OCTOPUS", "CANVAS", "COMPASS", "BYPASS", "TRESPASS", "EMBARRASS", "HARASS",
    "ABYSS", "DISCUS", "CHASSIS", "DEBRIS", "CORPS", "RENDEZVOUS", "ALWAYS", "PERHAPS",
    # Double-S singular nouns/verbs
    "GLASS", "GRASS", "BRASS", "KISS", "MISS", "BLISS", "DRESS", "PRESS", "GUESS",
    "CHESS", "CROSS", "MOSS", "BOSS", "LOSS", "FLOSS", "FUSS", "PASS", "CLASS",
    "MASS", "BASS", "LESS", "MESS", "ACROSS", "BLESS", "CONFESS", "DISMISS", "EXPRESS",
    "IMPRESS", "OPPRESS", "POSSESS", "PROCESS", "PROFESS", "PROGRESS", "RECESS",
    "STRESS", "SUCCESS", "SUPPRESS", "ACCESS", "ADDRESS", "COMPASS", "EMBARRASS",
    # Academic singulars ending in -ICS
    "PHYSICS", "MATHEMATICS", "ECONOMICS", "STATISTICS", "ETHICS", "OPTICS",
    "AERODYNAMICS", "THERMODYNAMICS", "ELECTRONICS", "ACOUSTICS", "GENETICS",
    "LINGUISTICS", "POLITICS", "ATHLETICS", "GYMNASTICS", "AEROBICS", "CLASSICS",
    "MECHANICS", "ROBOTICS", "DYNAMICS", "METRICS", "TACTICS", "LOGISTICS",
    # Additional common words
    "AS", "IS", "US", "HIS", "ITS", "HAS", "WAS", "DOES", "GOES", "NEWS", "LENS",
    # Pronouns, adverbs and set phrases that look like X + S but are not plurals
    "HERS", "OURS", "YOURS", "THEIRS", "BESIDES", "TOWARDS", "AFTERWARDS", "BACKWARDS", "FORWARDS",
    "SOMETIMES", "NOWADAYS", "UPSTAIRS", "DOWNSTAIRS", "INDOORS", "OUTDOORS", "OVERSEAS", "WHEREABOUTS",
    "HEADQUARTERS", "CLOTHES", "THANKS", "ODDS", "DATA", "MEDIA",
}


class DictionaryCleaner:
    """Preprocesses a raw English dictionary to filter out identifiable plurals."""

    def __init__(self, raw_vocab: Optional[Set[str]] = None):
        self.raw_vocab: Set[str] = {w.upper() for w in raw_vocab} if raw_vocab else set()
        self._inflect_engine = None
        self._init_inflect()

    def _init_inflect(self):
        try:
            import inflect
            self._inflect_engine = inflect.engine()
        except ImportError:
            self._inflect_engine = None

    def is_plural(self, word: str, reference_vocab: Set[str]) -> Tuple[bool, str]:
        """Determines if a word is an identifiable plural form.
        
        Returns:
            (is_plural: bool, reason: str)
        """
        w = word.upper()

        # 1. Explicit preserve list
        if w in PRESERVED_SINGULARS:
            return False, "preserved_singular"

        # 2. Known irregular plural check
        if w in IRREGULAR_PLURAL_MAP:
            return True, f"irregular_plural_of_{IRREGULAR_PLURAL_MAP[w]}"

        # 3. If it does not end in S, it's not a regular plural
        if not w.endswith("S"):
            return False, "singular_non_s"

        # 4. Words ending in SS that are not in irregular plurals are usually singular stems
        # e.g. GLASS, GRASS, KISS, MISS, CHESS, PASS, CROSS.
        # But KISSES, GLASSES end in SES, so w ends in S but not SS.
        if w.endswith("SS"):
            return False, "ends_in_double_s"

        # 5. Advanced morphological verification
        w_lower = w.lower()

        # Check via inflect if available
        if self._inflect_engine:
            sing = self._inflect_engine.singular_noun(w_lower)
            if sing and sing != w_lower:
                sing_upper = sing.upper()
                # Ensure the candidate singular is a legitimate word in English
                if sing_upper in reference_vocab or sing_upper in PRESERVED_SINGULARS:
                    # Verify bidirectional consistency
                    plural_of_sing = self._inflect_engine.plural(sing).lower()
                    if plural_of_sing == w_lower:
                        return True, f"inflect_plural_of_{sing_upper}"
                    # Common plural suffix checks (e.g. -es, -s, -ies)
                    if (
                        sing_upper + "S" == w
                        or sing_upper + "ES" == w
                        or (sing_upper.endswith("Y") and sing_upper[:-1] + "IES" == w)
                    ):
                        return True, f"regular_plural_of_{sing_upper}"

        # 6. Conservative fallback regular plural detection:
        # Check standard regular suffixes:
        # a) -IES -> -Y (e.g. BABIES -> BABY)
        if w.endswith("IES") and len(w) > 4:
            stem_y = w[:-3] + "Y"
            if stem_y in reference_vocab:
                return True, f"regular_plural_ies_of_{stem_y}"

        # b) -ES -> base (e.g. BOXES -> BOX, WATCHES -> WATCH, BUSES -> BUS)
        if w.endswith("ES") and len(w) > 3:
            stem = w[:-2]
            if stem in reference_vocab and (
                stem.endswith("X")
                or stem.endswith("CH")
                or stem.endswith("SH")
                or stem.endswith("S")
                or stem.endswith("Z")
            ):
                return True, f"regular_plural_es_of_{stem}"

        # c) -S -> base (e.g. CATS -> CAT, DOGS -> DOG)
        if w.endswith("S") and len(w) > 2:
            stem = w[:-1]
            if stem in reference_vocab and not stem.endswith("S"):
                # Ensure stem is not a tiny fragment unless it's a known short word
                return True, f"regular_plural_s_of_{stem}"

        return False, "singular_default"

    def clean_dictionary(
        self,
        raw_words: Set[str],
        min_word_length: int = 2,
    ) -> Tuple[Set[str], Dict[str, int]]:
        """Cleans raw words according to the plural exclusion policy.
        
        Returns:
            (accepted_words, statistics_dict)
        """
        # Normalize and deduplicate
        normalized: Set[str] = {
            w.strip().upper()
            for w in raw_words
            if w.strip() and w.strip().isalpha() and len(w.strip()) >= min_word_length
        }

        accepted: Set[str] = set()
        excluded: Set[str] = set()
        irregular_excluded: int = 0
        regular_excluded: int = 0

        for word in normalized:
            is_pl, reason = self.is_plural(word, normalized)
            if is_pl:
                excluded.add(word)
                if "irregular" in reason:
                    irregular_excluded += 1
                else:
                    regular_excluded += 1
            else:
                accepted.add(word)

        stats = {
            "original_count": len(raw_words),
            "normalized_count": len(normalized),
            "accepted_count": len(accepted),
            "excluded_count": len(excluded),
            "irregular_excluded": irregular_excluded,
            "regular_excluded": regular_excluded,
        }

        return accepted, stats
