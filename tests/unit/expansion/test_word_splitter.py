from psh.expansion.word_splitter import WordSplitter


def test_word_splitter_default_ifs_multiple_words():
    splitter = WordSplitter()
    result = splitter.split('one two\tthree\nfour', ' \t\n')
    assert result == ['one', 'two', 'three', 'four']


def test_word_splitter_returns_original_when_no_split():
    splitter = WordSplitter()
    result = splitter.split('single', ' \t\n')
    assert result == ['single']


def test_word_splitter_handles_empty_ifs():
    splitter = WordSplitter()
    result = splitter.split('a b c', '')
    assert result == ['a b c']
