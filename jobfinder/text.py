import re
import unicodedata


def norm(s):
    """Minúsculas, sin tildes, espacios compactados."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.lower()).strip()


_cache = {}


def term_re(term):
    """Regex de palabra completa para un término ya normalizado (sirve para '.net', 'c#', 'c++')."""
    r = _cache.get(term)
    if r is None:
        r = _cache[term] = re.compile(r"(?<![a-z0-9])" + re.escape(norm(term)) + r"(?![a-z0-9#+])")
    return r


def has(text, term):
    return bool(term_re(term).search(text))


def found(text, terms):
    return [t for t in terms if has(text, t)]
