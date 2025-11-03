"""Word splitting implementation for shell expansions."""

from typing import List, Optional


class WordSplitter:
    """Split words according to the shell's IFS rules."""

    def split(self, text: str, ifs: Optional[str]) -> List[str]:
        """Split text using IFS characters.

        Args:
            text: The string to split.
            ifs: The shell's IFS value (None or empty string disables splitting).

        Returns:
            List of resulting words. If no splitting occurs, returns the original string as a single element.
        """
        if text is None:
            return []

        if not ifs:
            return [text]

        words: List[str] = []
        current_word: List[str] = []

        for char in text:
            if char in ifs:
                if current_word:
                    words.append(''.join(current_word))
                    current_word = []
            else:
                current_word.append(char)

        if current_word:
            words.append(''.join(current_word))

        if len(words) > 1:
            return words

        return [text]
