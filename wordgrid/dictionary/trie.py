from typing import Dict, List, Optional


class TrieNode:
    """A node in the prefix Trie."""

    __slots__ = ("children", "is_terminal")

    def __init__(self):
        self.children: Dict[str, "TrieNode"] = {}
        self.is_terminal: bool = False


class Trie:
    """Prefix Trie for high-performance dictionary lookup and prefix testing."""

    def __init__(self):
        self.root = TrieNode()
        self.word_count: int = 0

    def insert(self, word: str) -> None:
        """Inserts an uppercase word into the Trie."""
        word = word.strip().upper()
        if not word:
            return

        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        if not node.is_terminal:
            node.is_terminal = True
            self.word_count += 1

    def is_word(self, word: str) -> bool:
        """Checks if the exact word exists in the Trie in O(L) time."""
        word = word.strip().upper()
        if not word:
            return False

        node = self.root
        for char in word:
            node = node.children.get(char)
            if node is None:
                return False
        return node.is_terminal

    def is_prefix(self, prefix: str) -> bool:
        """Checks if prefix exists in any word in the Trie in O(L) time."""
        prefix = prefix.strip().upper()
        if not prefix:
            return True

        node = self.root
        for char in prefix:
            node = node.children.get(char)
            if node is None:
                return False
        return True

    def get_words_with_prefix(self, prefix: str, max_words: int = 50) -> List[str]:
        """Finds words starting with prefix (useful for AI partial sequence analysis)."""
        prefix = prefix.strip().upper()
        node = self.root
        for char in prefix:
            node = node.children.get(char)
            if node is None:
                return []

        results: List[str] = []

        def _dfs(curr: TrieNode, current_str: List[str]):
            if len(results) >= max_words:
                return
            if curr.is_terminal:
                results.append("".join(current_str))
            for char, next_node in sorted(curr.children.items()):
                current_str.append(char)
                _dfs(next_node, current_str)
                current_str.pop()

        _dfs(node, list(prefix))
        return results

    def __len__(self) -> int:
        return self.word_count

    def __contains__(self, word: str) -> bool:
        return self.is_word(word)
