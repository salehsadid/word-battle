"""Dictionary subsystem for WordGrid."""

from wordgrid.dictionary.trie import Trie, TrieNode
from wordgrid.dictionary.cleaner import DictionaryCleaner, IRREGULAR_PLURAL_MAP, PRESERVED_SINGULARS
from wordgrid.dictionary.word_validator import WordValidator
from wordgrid.dictionary.loader import DictionaryLoader

__all__ = [
    "Trie",
    "TrieNode",
    "DictionaryCleaner",
    "IRREGULAR_PLURAL_MAP",
    "PRESERVED_SINGULARS",
    "WordValidator",
    "DictionaryLoader",
]
