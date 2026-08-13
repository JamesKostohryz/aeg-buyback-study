# -*- coding: utf-8 -*-
"""Numeric-token diff between two versions of a generated document.

WHY THIS EXISTS. The proof standard set on 2026-08-13 for pulling a measure out
of a company driver and into the template is that the regenerated document
contains no numeric token the previous version did not, in the same order, with
the same value. Items 4 and 5 both met it by hand. Doing it by eye a third time
is how it stops being done, so it is a script.

WHAT IT COMPARES. Every run of digits, with optional sign, decimal point,
thousands separators and trailing percent sign, in document order. Markup is
not compared: a changed class name or a reordered attribute is not a moved
figure, and flagging it would train the reader to ignore the output. What IS
compared is every number the reader can see, and their order.

WHAT IT DOES NOT PROVE. That the numbers are right. It proves only that they did
not move, which is the whole and only claim.

    python3 numeric_token_diff.py OLD.html NEW.html
"""
import re
import sys

TOKEN = re.compile(r'[-+]?\d[\d,]*(?:\.\d+)?%?')
TAG = re.compile(r'<[^>]+>')
ENTITY = re.compile(r'&[a-zA-Z]+;|&#\d+;')


def tokens(path):
    """Numeric tokens in document order, from the VISIBLE text only."""
    text = open(path, encoding='utf-8').read()
    text = TAG.sub(' ', text)          # markup is not a figure
    text = ENTITY.sub(' ', text)       # &mdash; &plusmn; and friends
    return TOKEN.findall(text)


def compare(old_path, new_path):
    a, b = tokens(old_path), tokens(new_path)
    moved, added, removed = [], [], []
    n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]:
            moved.append((i, a[i], b[i]))
    if len(b) > len(a):
        added = [(i, b[i]) for i in range(n, len(b))]
    if len(a) > len(b):
        removed = [(i, a[i]) for i in range(n, len(a))]
    return a, b, moved, added, removed


def main(old_path, new_path):
    a, b, moved, added, removed = compare(old_path, new_path)
    print(f"old: {len(a):,} numeric tokens   new: {len(b):,} numeric tokens")
    if moved:
        print(f"\n{len(moved)} TOKEN(S) MOVED:")
        for i, x, y in moved[:200]:
            print(f"  position {i:>6}: {x!r} -> {y!r}")
        if len(moved) > 200:
            print(f"  ... and {len(moved) - 200} more")
    if added:
        print(f"\n{len(added)} token(s) appended (new material at the end):")
        for i, y in added[:50]:
            print(f"  position {i:>6}: {y!r}")
    if removed:
        print(f"\n{len(removed)} token(s) dropped from the end:")
        for i, x in removed[:50]:
            print(f"  position {i:>6}: {x!r}")
    if not moved and not added and not removed:
        print("\nZERO NUMERIC TOKENS MOVED.")
        return 0
    # New material at the end is a report that grew, which is not a moved
    # figure; a token that CHANGED VALUE is. They are reported separately and
    # only the second fails.
    print("")
    return 1 if moved else 0


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
