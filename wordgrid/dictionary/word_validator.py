from typing import Optional, List
from wordgrid.dictionary.trie import Trie


# Wraps Trie to provide high-performance word validation and prefix querying.
class WordValidator:

    # Wrap a trie (or a new empty one).
    def __init__(self, trie: Optional[Trie] = None):
        self.trie = trie or Trie()

    # Checks if uppercase word is accepted in the dictionary.
    def is_valid_word(self, word: str) -> bool:
        return self.trie.is_word(word)

    # Checks if uppercase prefix can lead to any valid accepted word.
    def is_valid_prefix(self, prefix: str) -> bool:
        return self.trie.is_prefix(prefix)

    # Returns words matching prefix.
    def get_completions(self, prefix: str, max_results: int = 20) -> List[str]:
        return self.trie.get_words_with_prefix(prefix, max_results)

    # Number of words in the dictionary.
    def __len__(self) -> int:
        return len(self.trie)

    # Allows `word in validator`.
    def __contains__(self, word: str) -> bool:
        return self.is_valid_word(word)
