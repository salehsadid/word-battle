from typing import Dict, List, Optional


# A node in the prefix Trie.
class TrieNode:

    __slots__ = ("children", "is_terminal")

    # A node has child letters and a flag that marks the end of a word.
    def __init__(self):
        self.children: Dict[str, "TrieNode"] = {}
        self.is_terminal: bool = False


# Prefix Trie for high-performance dictionary lookup and prefix testing.
class Trie:

    # Start with an empty root node and no words.
    def __init__(self):
        self.root = TrieNode()
        self.word_count: int = 0

    # Inserts an uppercase word into the Trie.
    def insert(self, word: str) -> None:
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

    # Checks if the exact word exists in the Trie in O(L) time.
    def is_word(self, word: str) -> bool:
        word = word.strip().upper()
        if not word:
            return False

        node = self.root
        for char in word:
            node = node.children.get(char)
            if node is None:
                return False
        return node.is_terminal

    # Checks if prefix exists in any word in the Trie in O(L) time.
    def is_prefix(self, prefix: str) -> bool:
        prefix = prefix.strip().upper()
        if not prefix:
            return True

        node = self.root
        for char in prefix:
            node = node.children.get(char)
            if node is None:
                return False
        return True

    # Finds words starting with prefix (useful for AI partial sequence analysis).
    def get_words_with_prefix(self, prefix: str, max_words: int = 50) -> List[str]:
        prefix = prefix.strip().upper()
        node = self.root
        for char in prefix:
            node = node.children.get(char)
            if node is None:
                return []

        results: List[str] = []

        # Depth-first walk that collects words below this node.
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

    # Number of words in the trie.
    def __len__(self) -> int:
        return self.word_count

    # Allows `word in trie`.
    def __contains__(self, word: str) -> bool:
        return self.is_word(word)
