from typing import Optional, List
from wordgrid.dictionary.trie import Trie


class WordValidator:
    """Wraps Trie to provide high-performance word validation and prefix querying."""

    def __init__(self, trie: Optional[Trie] = None):
        self.trie = trie or Trie()

    def is_valid_word(self, word: str) -> bool:
        """Checks if uppercase word is accepted in the dictionary."""
        return self.trie.is_word(word)

    def is_valid_prefix(self, prefix: str) -> bool:
        """Checks if uppercase prefix can lead to any valid accepted word."""
        return self.trie.is_prefix(prefix)

    def get_completions(self, prefix: str, max_results: int = 20) -> List[str]:
        """Returns words matching prefix."""
        return self.trie.get_words_with_prefix(prefix, max_results)

    def __len__(self) -> int:
        return len(self.trie)

    def __contains__(self, word: str) -> bool:
        return self.is_valid_word(word)
