import os
from pathlib import Path
from typing import Tuple, Dict, Any, Optional, Set
from wordgrid.dictionary.trie import Trie
from wordgrid.dictionary.word_validator import WordValidator
from wordgrid.dictionary.cleaner import DictionaryCleaner
from wordgrid.config import (
    RAW_DICT_PATH,
    CLEANED_DICT_PATH,
    TEST_DICT_PATH,
    DATA_DIR,
)

# Standard starter test vocabulary for fast reproducible unit tests
TEST_VOCABULARY = [
    # Singular nouns & verbs
    "CAT", "DOG", "TREE", "HOUSE", "CAR", "BAT", "RAT", "FOX", "BOX",
    "BUS", "GAS", "LENS", "ANALYSIS", "GLASS", "GRASS", "KISS", "MOUSE", "TOOTH",
    "MAN", "CHILD", "FOOT", "OX", "GOOSE", "CRISIS", "PLAY", "GAME", "WORD", "GRID",
    "WIN", "TIE", "LOSE", "ROW", "COL", "NET", "SET", "BET", "RUN", "SUN",
    "AT", "TO", "IN", "ON", "HE", "ME", "WE", "IT", "IS", "AS",
    # Plurals included in test file to verify they get filtered
    "CATS", "DOGS", "TREES", "HOUSES", "CARS", "BATS", "RATS", "FOXES", "BOXES",
    "BUSES", "GASES", "LENSES", "ANALYSES", "GLASSES", "KISSES", "MICE", "TEETH",
    "MEN", "CHILDREN", "FEET", "OXEN", "GEESE", "CRISES",
]


# Manages loading, offline caching, and preprocessing of English word dictionaries.
class DictionaryLoader:

    # Create the data folder if it does not exist.
    @staticmethod
    def ensure_data_directory():
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Creates the default test dictionary file if it doesn't already exist.
    @classmethod
    def create_default_test_file(cls, path: Optional[Path] = None) -> Path:
        cls.ensure_data_directory()
        target = path or TEST_DICT_PATH
        if not target.exists():
            with open(target, "w", encoding="utf-8") as f:
                for word in sorted(TEST_VOCABULARY):
                    f.write(f"{word}\n")
        return target

    # Loads and normalizes uppercase words from a text file.
    @classmethod
    def load_words_from_file(cls, file_path: Path) -> Set[str]:
        if not file_path.exists():
            raise FileNotFoundError(
                f"Dictionary file not found at: {file_path}\n"
                f"Please ensure an offline English dictionary is provided in the 'data/' directory."
            )
        words: Set[str] = set()
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                w = line.strip().upper()
                if w and w.isalpha():
                    words.add(w)
        return words

    # Preprocesses the raw word list and saves the cleaned dictionary locally.
    @classmethod
    def prepare_and_clean_dictionary(
        cls,
        raw_path: Optional[Path] = None,
        cleaned_path: Optional[Path] = None,
        min_word_length: int = 2,
    ) -> Tuple[Set[str], Dict[str, Any]]:
        cls.ensure_data_directory()
        raw_p = raw_path or RAW_DICT_PATH
        cleaned_p = cleaned_path or CLEANED_DICT_PATH

        if not raw_p.exists():
            # If raw file is missing, try to create an initial word list or fallback to test list
            cls.create_default_test_file(TEST_DICT_PATH)
            raw_p = TEST_DICT_PATH

        raw_words = cls.load_words_from_file(raw_p)
        cleaner = DictionaryCleaner(raw_words)
        accepted_words, stats = cleaner.clean_dictionary(raw_words, min_word_length)

        # Save to cleaned file
        with open(cleaned_p, "w", encoding="utf-8") as f:
            for w in sorted(accepted_words):
                f.write(f"{w}\n")

        return accepted_words, stats

    # Loads accepted dictionary into a WordValidator.
    @classmethod
    def load_dictionary(
        cls,
        dict_path: Optional[Path] = None,
        force_clean: bool = False,
        min_word_length: int = 2,
    ) -> Tuple[WordValidator, Dict[str, Any]]:
        cls.ensure_data_directory()
        cleaned_p = dict_path or CLEANED_DICT_PATH

        stats: Dict[str, Any] = {}
        if not cleaned_p.exists() or force_clean:
            accepted_words, stats = cls.prepare_and_clean_dictionary(
                raw_path=RAW_DICT_PATH,
                cleaned_path=cleaned_p,
                min_word_length=min_word_length,
            )
        else:
            accepted_words = cls.load_words_from_file(cleaned_p)
            stats = {
                "accepted_count": len(accepted_words),
                "loaded_from_cache": str(cleaned_p),
            }

        trie = Trie()
        for word in accepted_words:
            trie.insert(word)

        return WordValidator(trie), stats

    # Loads a clean test dictionary for deterministic unit tests.
    @classmethod
    def load_test_dictionary(cls) -> WordValidator:
        cls.create_default_test_file()
        words = cls.load_words_from_file(TEST_DICT_PATH)
        cleaner = DictionaryCleaner(words)
        accepted, _ = cleaner.clean_dictionary(words)
        trie = Trie()
        for w in accepted:
            trie.insert(w)
        return WordValidator(trie)
