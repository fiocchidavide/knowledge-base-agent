"""Resolve a Calibre book's file on disk.

Calibre's metadata.db stores the *logical* title in books.path and data.name,
but sanitises the filesystem: an apostrophe becomes '_', and other characters
may be substituted too. Constructing a path from the DB alone silently fails
for those books -- it cost 4 of 115 here (#138, #224, #232, #234), each of
which looked like an unreadable scan until the path was fixed.
"""
import glob, os, re, sqlite3

LIB = os.path.expanduser("~/Calibre Library")

def _sanitise(s):
    # Calibre's own substitution for path-hostile characters
    return re.sub(r"[\'\"\?\*\:\<\>\|]", "_", s)

def resolve(book_id, lib=LIB):
    c = sqlite3.connect(os.path.join(lib, "metadata.db"))
    row = c.execute("""select b.path, dd.name, lower(dd.format)
                       from books b join data dd on dd.book=b.id where b.id=?""",
                    (book_id,)).fetchone()
    if not row: return None
    path, name, fmt = row
    for cand in (os.path.join(lib, path, f"{name}.{fmt}"),
                 os.path.join(lib, _sanitise(path), f"{_sanitise(name)}.{fmt}")):
        if os.path.exists(cand): return cand
    # last resort: the id is in the folder name, so glob for it
    for d in glob.glob(os.path.join(lib, "*", f"*({book_id})")):
        hits = glob.glob(os.path.join(d, f"*.{fmt}"))
        if hits: return hits[0]
    return None

def resolve_all(lib=LIB):
    c = sqlite3.connect(os.path.join(lib, "metadata.db"))
    return {bid: resolve(bid, lib) for (bid,) in c.execute("select id from books")}
