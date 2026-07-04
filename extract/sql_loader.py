"""Load SQL statements from the dedicated `extract/sql/` directory.

DIDACTIC NOTE — Why SQL lives in .sql files, not Python strings:
    1. Reviewability: a reviewer sees real SQL with syntax highlighting in
       the PR diff, not an f-string blob.
    2. Tooling: linters (sqlfluff), formatters and IDEs work on .sql files.
    3. Separation of concerns: Python orchestrates, SQL declares. This is
       exactly dbt's philosophy applied to the extract layer — the whole
       project speaks one design language.
    4. Reuse: the same MERGE statement is used by every indicator because
       the raw table is generic.

SECURITY NOTE (OWASP — SQL Injection):
    These files use %(name)s placeholders resolved by psycopg on the
    SERVER side (parametrised queries). We NEVER interpolate user/config
    values into SQL text with f-strings. The only exception is DDL, which
    contains no external input at all.
"""

from functools import lru_cache
from pathlib import Path

SQL_DIR = Path(__file__).parent / "sql"


@lru_cache(maxsize=None)
def load_sql(relative_path: str) -> str:
    """Return the content of a SQL file, e.g. load_sql("merge/merge_indicator_values.sql").

    Cached because files never change at runtime; avoids re-reading from
    disk on every pipeline iteration.
    """
    path = SQL_DIR / relative_path
    if not path.is_file():
        available = sorted(str(p.relative_to(SQL_DIR)) for p in SQL_DIR.rglob("*.sql"))
        raise FileNotFoundError(
            f"SQL file not found: {relative_path}. Available: {available}"
        )
    return path.read_text(encoding="utf-8")
