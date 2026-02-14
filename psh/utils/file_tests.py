"""File test utilities for shell operations."""
import os


def file_newer_than(file1: str, file2: str) -> bool:
    """Check if file1 is newer than file2."""
    try:
        stat1 = os.stat(file1)
        stat2 = os.stat(file2)
        return stat1.st_mtime > stat2.st_mtime
    except FileNotFoundError:
        return False


def file_older_than(file1: str, file2: str) -> bool:
    """Check if file1 is older than file2."""
    try:
        stat1 = os.stat(file1)
        stat2 = os.stat(file2)
        return stat1.st_mtime < stat2.st_mtime
    except FileNotFoundError:
        return False


def files_same(file1: str, file2: str) -> bool:
    """Check if two files are the same (same inode)."""
    try:
        stat1 = os.stat(file1)
        stat2 = os.stat(file2)
        return (stat1.st_dev == stat2.st_dev and
                stat1.st_ino == stat2.st_ino)
    except FileNotFoundError:
        return False
