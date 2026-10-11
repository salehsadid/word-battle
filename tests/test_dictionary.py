import pytest
from wordgrid.dictionary.trie import Trie
from wordgrid.dictionary.cleaner import DictionaryCleaner, PRESERVED_SINGULARS, IRREGULAR_PLURAL_MAP
from wordgrid.dictionary.word_validator import WordValidator
from wordgrid.dictionary.loader import DictionaryLoader


def test_trie_basic_operations():
    trie = Trie()
    trie.insert("CAT")
    trie.insert("CAR")
    trie.insert("CART")

    assert trie.is_word("CAT")
    assert trie.is_word("CAR")
    assert trie.is_word("CART")
    assert not trie.is_word("CA")
    assert not trie.is_word("DOG")

    assert trie.is_prefix("C")
    assert trie.is_prefix("CA")
    assert trie.is_prefix("CAR")
    assert not trie.is_prefix("D")


def test_singular_words_remain_in_cleaned_dictionary():
    raw_words = {"CAT", "CATS", "DOG", "DOGS", "HOUSE", "HOUSES", "MOUSE", "MICE", "TOOTH", "TEETH"}
    cleaner = DictionaryCleaner(raw_words)
    accepted, stats = cleaner.clean_dictionary(raw_words)

    # Singulars must remain
    assert "CAT" in accepted
    assert "DOG" in accepted
    assert "HOUSE" in accepted
    assert "MOUSE" in accepted
    assert "TOOTH" in accepted


def test_regular_plurals_excluded():
    raw_words = {"CAT", "CATS", "DOG", "DOGS", "BOX", "BOXES", "CAR", "CARS"}
    cleaner = DictionaryCleaner(raw_words)
    accepted, stats = cleaner.clean_dictionary(raw_words)

    assert "CATS" not in accepted
    assert "DOGS" not in accepted
    assert "BOXES" not in accepted
    assert "CARS" not in accepted
    assert stats["regular_excluded"] >= 4


def test_irregular_plurals_excluded():
    raw_words = {"MOUSE", "MICE", "TOOTH", "TEETH", "MAN", "MEN", "CHILD", "CHILDREN", "FOOT", "FEET", "GOOSE", "GEESE", "OX", "OXEN"}
    cleaner = DictionaryCleaner(raw_words)
    accepted, stats = cleaner.clean_dictionary(raw_words)

    assert "MICE" not in accepted
    assert "TEETH" not in accepted
    assert "MEN" not in accepted
    assert "CHILDREN" not in accepted
    assert "FEET" not in accepted
    assert "GEESE" not in accepted
    assert "OXEN" not in accepted
    assert stats["irregular_excluded"] >= 7


def test_valid_singular_words_ending_in_s_preserved():
    raw_words = {"BUS", "BUSES", "ANALYSIS", "ANALYSES", "GAS", "GASES", "LENS", "LENSES", "GLASS", "GLASSES", "KISS", "KISSES", "CRISIS", "CRISES"}
    cleaner = DictionaryCleaner(raw_words)
    accepted, stats = cleaner.clean_dictionary(raw_words)

    # Preserved singulars ending in S MUST remain
    assert "BUS" in accepted
    assert "ANALYSIS" in accepted
    assert "GAS" in accepted
    assert "LENS" in accepted
    assert "GLASS" in accepted
    assert "KISS" in accepted
    assert "CRISIS" in accepted

    # Their plurals must be excluded
    assert "BUSES" not in accepted
    assert "ANALYSES" not in accepted
    assert "GASES" not in accepted
    assert "LENSES" not in accepted
    assert "GLASSES" not in accepted
    assert "KISSES" not in accepted
    assert "CRISES" not in accepted


def test_word_validator_interface():
    trie = Trie()
    trie.insert("HELLO")
    validator = WordValidator(trie)

    assert validator.is_valid_word("HELLO")
    assert validator.is_valid_word("hello")  # case normalization
    assert not validator.is_valid_word("WORLD")
    assert validator.is_valid_prefix("HEL")
    assert not validator.is_valid_prefix("WOR")


def test_dictionary_loader_offline_and_stats():
    validator, stats = DictionaryLoader.load_dictionary()
    assert len(validator) > 1000
    assert validator.is_valid_word("CAT")
    assert not validator.is_valid_word("CATS")
    assert validator.is_valid_word("BUS")
    assert not validator.is_valid_word("BUSES")
    assert validator.is_valid_word("ANALYSIS")
    assert not validator.is_valid_word("ANALYSES")
