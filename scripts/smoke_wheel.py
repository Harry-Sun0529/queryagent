"""Smoke-test an installed wheel from outside the source tree (v1.0 T48, H13).

Run it with the interpreter of a clean virtualenv the wheel was installed into:

    python -m venv /tmp/clean && /tmp/clean/bin/pip install dist/queryagent-*.whl
    /tmp/clean/bin/python scripts/smoke_wheel.py dist/queryagent-*.whl

It checks four things:

- the package imported is the installed one, not a checkout;
- the wheel holds only the package and its metadata: no example configs, no
  credentials;
- `queryagent --help` works;
- a confirmed SQLite flow runs end to end through the console script and
  prints the right count.
"""

from __future__ import annotations

import sqlite3
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REQUIRED = (
    "queryagent/py.typed",
    "queryagent/cli.py",
    "queryagent/mcp/server.py",
    "queryagent/web/server.py",
    "queryagent/workflow/wiring.py",
)
FORBIDDEN = (".env", "docker-compose", "secret", "config.yaml", ".db")


def check_wheel(wheel: Path) -> None:
    names = zipfile.ZipFile(wheel).namelist()
    outside = [n for n in names if not n.startswith("queryagent/") and ".dist-info/" not in n]
    if outside:
        raise SystemExit(f"the wheel carries files outside the package: {outside}")
    risky = [n for n in names if any(mark in n.lower() for mark in FORBIDDEN)]
    if risky:
        raise SystemExit(f"the wheel carries files that look like configuration or data: {risky}")
    missing = [n for n in REQUIRED if n not in names]
    if missing:
        raise SystemExit(f"the wheel lacks {missing}")


def check_installed() -> str:
    import queryagent

    location = Path(queryagent.__file__).resolve()
    if Path(sys.prefix).resolve() not in location.parents:
        raise SystemExit(f"imported {location}, which is not the installed wheel")
    return queryagent.__version__


def check_flow() -> None:
    console = Path(sys.executable).parent / "queryagent"
    subprocess.run([str(console), "--help"], check=True, capture_output=True)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        connection = sqlite3.connect(root / "shop.db")
        connection.execute("CREATE TABLE users (id INTEGER, channel TEXT)")
        connection.executemany(
            "INSERT INTO users VALUES (?,?)", [(1, "ads"), (2, "organic"), (3, "internal_test")]
        )
        connection.commit()
        connection.close()
        (root / "metrics.yaml").write_text(
            "metrics:\n  - name: new_users\n    display_name: 新增用户\n"
            "    definition: 统计新加入的用户数。\n    variants:\n"
            "      - {key: registered, label: 注册口径, definition: 按注册计数}\n",
            encoding="utf-8",
        )
        (root / "mappings.yaml").write_text(
            "mappings:\n  - metric: new_users\n    variant: registered\n"
            "    sql: \"SELECT COUNT(*) AS n FROM users WHERE channel <> 'internal_test'\"\n",
            encoding="utf-8",
        )
        (root / "config.yaml").write_text(
            "llm: {backend: openai_compatible, model: m, base_url: 'https://x.invalid'}\n"
            f"database: {{type: sqlite, path: '{root / 'shop.db'}'}}\n"
            f"metrics_path: '{root / 'metrics.yaml'}'\n"
            f"workflow: {{mappings_path: '{root / 'mappings.yaml'}', "
            f"state_path: '{root / 'workflow.db'}'}}\ntrace: false\n",
            encoding="utf-8",
        )
        done = subprocess.run(
            [str(console), "flow", "新增用户有多少？", "--config", str(root / "config.yaml"),
             "--variant", "registered", "--yes"],
            capture_output=True,
            text=True,
            cwd=root,
        )
        if done.returncode != 0 or "\n  2\n" not in done.stdout:
            raise SystemExit(f"flow failed ({done.returncode}):\n{done.stdout}\n{done.stderr}")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: smoke_wheel.py dist/queryagent-*.whl")
    check_wheel(Path(sys.argv[1]))
    version = check_installed()
    check_flow()
    print(f"wheel smoke ok: queryagent {version}")


if __name__ == "__main__":
    main()
