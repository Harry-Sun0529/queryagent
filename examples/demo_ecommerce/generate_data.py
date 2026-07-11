"""Generate the fictional ``demo_shop`` dataset (spec §五, AI-OWNED).

Rows are built in a dialect-agnostic intermediate representation (IR) and
handed to per-dialect emitters: MySQL init SQL (v0.1.0, docker path) and a
SQLite file ``demo_shop.db`` (v0.1.1, the Docker-free demo path). A
ClickHouse replica reuses the same IR if it survives the schedule cut.

The RNG is seeded (deterministic data shape), but dates are generated
relative to *today* so demo questions like "上个月每天的新增用户数" always
have non-trivial answers.

The metric-ambiguity seed for later versions lives in the schema itself:
``users.created_at`` (registration) vs ``users.first_order_at`` (first paid
order) are two competing definitions of "new user".

Usage:
    python examples/demo_ecommerce/generate_data.py [--out DIR]
"""

from __future__ import annotations

import argparse
import random
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

SEED = 42
N_USERS = 50_000
DAYS = 180
ORDER_USER_RATIO = 0.62
MEAN_EXTRA_ORDERS = 5.5  # buyers place 1 + Exp(mean) orders
BATCH = 1_000

Value = int | float | str | datetime | None
Row = tuple[Value, ...]


@dataclass(frozen=True)
class Column:
    """IR column: name, abstract type, nullability, comment."""

    name: str
    ir_type: str  # "id" | "int" | "decimal" | "varchar" | "datetime" | "bool"
    nullable: bool = False
    comment: str = ""


@dataclass(frozen=True)
class Table:
    """IR table: columns plus index metadata for emitters that support it."""

    name: str
    columns: tuple[Column, ...]
    comment: str = ""
    primary_key: tuple[str, ...] = ()
    indexes: tuple[tuple[str, ...], ...] = ()


TABLES: tuple[Table, ...] = (
    Table(
        name="users",
        comment="registered users",
        primary_key=("id",),
        indexes=(("created_at",), ("first_order_at",)),
        columns=(
            Column("id", "id"),
            Column("created_at", "datetime", comment="registration time (growth-team anchor)"),
            Column(
                "first_order_at",
                "datetime",
                nullable=True,
                comment="first paid order time (ops-team anchor)",
            ),
            Column("channel", "varchar", comment="acquisition channel code, see channels"),
            Column("region", "varchar"),
        ),
    ),
    Table(
        name="orders",
        comment="orders, one row per checkout",
        primary_key=("id",),
        indexes=(("user_id",), ("created_at",)),
        columns=(
            Column("id", "id"),
            Column("user_id", "id"),
            Column("amount", "decimal", comment="order total = sum of its items"),
            Column("status", "varchar", comment="paid | refunded | canceled"),
            Column("created_at", "datetime"),
        ),
    ),
    Table(
        name="order_items",
        comment="line items",
        indexes=(("order_id",),),
        columns=(
            Column("order_id", "id"),
            Column("sku", "varchar"),
            Column("qty", "int"),
            Column("price", "decimal", comment="unit price"),
        ),
    ),
    Table(
        name="channels",
        comment="acquisition channels",
        primary_key=("code",),
        columns=(
            Column("code", "varchar"),
            Column("name", "varchar"),
            Column("is_paid", "bool"),
        ),
    ),
)

CHANNELS: tuple[tuple[str, str, int], ...] = (
    ("organic", "Organic search & direct", 0),
    ("ads", "Paid advertising", 1),
    ("referral", "User referral", 0),
    ("internal_test", "Internal test accounts", 0),
)
CHANNEL_WEIGHTS = (50, 38, 7, 5)
REGIONS = ("north", "south", "east", "west", "overseas")


def generate(rng: random.Random, now: datetime) -> dict[str, list[Row]]:
    """Build all rows in the IR; emitters turn them into dialect SQL."""
    start = now - timedelta(days=DAYS)
    users: list[Row] = []
    orders: list[Row] = []
    items: list[Row] = []
    channel_codes = [c[0] for c in CHANNELS]
    order_id = 0
    for user_id in range(1, N_USERS + 1):
        created = start + timedelta(seconds=rng.random() * DAYS * 86_400)
        channel = rng.choices(channel_codes, weights=CHANNEL_WEIGHTS)[0]
        region = rng.choice(REGIONS)
        first_order_at: datetime | None = None
        if channel != "internal_test" and rng.random() < ORDER_USER_RATIO:
            candidate = created + timedelta(days=rng.expovariate(1 / 5.0))
            if candidate < now:
                first_order_at = candidate.replace(microsecond=0)
        created = created.replace(microsecond=0)
        users.append((user_id, created, first_order_at, channel, region))
        if first_order_at is None:
            continue
        extra = min(int(rng.expovariate(1 / MEAN_EXTRA_ORDERS)), 19)
        order_times = [first_order_at] + sorted(
            (first_order_at + (now - first_order_at) * rng.random()).replace(microsecond=0)
            for _ in range(extra)
        )
        for i, order_time in enumerate(order_times):
            order_id += 1
            amount = 0.0
            for _ in range(rng.randint(1, 3)):
                qty = rng.randint(1, 3)
                price = round(rng.uniform(9.9, 499.0), 2)
                items.append((order_id, f"SKU-{rng.randint(1, 500):04d}", qty, price))
                amount += qty * price
            # first_order_at is defined as the first *paid* order, keep it coherent
            status = "paid" if i == 0 else rng.choices(
                ["paid", "refunded", "canceled"], weights=[85, 5, 10]
            )[0]
            orders.append((order_id, user_id, round(amount, 2), status, order_time))
    return {
        "users": users,
        "orders": orders,
        "order_items": items,
        "channels": [tuple(c) for c in CHANNELS],
    }


# --- MySQL emitter ---------------------------------------------------------

MYSQL_TYPES = {
    "id": "BIGINT",
    "int": "INT",
    "decimal": "DECIMAL(12,2)",
    "varchar": "VARCHAR(64)",
    "datetime": "DATETIME",
    "bool": "TINYINT(1)",
}


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("'", "''")


def _sql_literal(value: Value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, datetime):
        return f"'{value.strftime('%Y-%m-%d %H:%M:%S')}'"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    return f"'{_escape(str(value))}'"


def _mysql_ddl(table: Table) -> str:
    lines = []
    for column in table.columns:
        null_sql = "NULL" if column.nullable else "NOT NULL"
        line = f"  `{column.name}` {MYSQL_TYPES[column.ir_type]} {null_sql}"
        if column.comment:
            line += f" COMMENT '{_escape(column.comment)}'"
        lines.append(line)
    if table.primary_key:
        keys = ", ".join(f"`{k}`" for k in table.primary_key)
        lines.append(f"  PRIMARY KEY ({keys})")
    for index in table.indexes:
        cols = ", ".join(f"`{c}`" for c in index)
        lines.append(f"  KEY `idx_{table.name}_{'_'.join(index)}` ({cols})")
    body = ",\n".join(lines)
    comment = f" COMMENT='{_escape(table.comment)}'" if table.comment else ""
    return f"CREATE TABLE `{table.name}` (\n{body}\n) ENGINE=InnoDB{comment};\n"


def emit_mysql(data: dict[str, list[Row]], out_path: Path) -> None:
    """Write DDL + batched INSERTs runnable by docker-entrypoint-initdb.d."""
    with out_path.open("w", encoding="utf-8") as f:
        f.write("-- Generated by generate_data.py; do not edit.\n")
        f.write("USE demo_shop;\nSET NAMES utf8mb4;\n\n")
        for table in TABLES:
            f.write(_mysql_ddl(table))
        f.write("\n")
        for table in TABLES:
            rows = data[table.name]
            col_list = ", ".join(f"`{c.name}`" for c in table.columns)
            for batch_start in range(0, len(rows), BATCH):
                batch = rows[batch_start : batch_start + BATCH]
                values = ",\n".join(
                    "(" + ", ".join(_sql_literal(v) for v in row) + ")" for row in batch
                )
                f.write(f"INSERT INTO `{table.name}` ({col_list}) VALUES\n{values};\n")


# --- ClickHouse emitter ----------------------------------------------------

CLICKHOUSE_TYPES = {
    "id": "Int64",
    "int": "Int32",
    "decimal": "Decimal(12, 2)",
    "varchar": "String",
    "datetime": "DateTime",
    "bool": "UInt8",
}


def _clickhouse_ddl(table: Table) -> str:
    lines = []
    for column in table.columns:
        ch_type = CLICKHOUSE_TYPES[column.ir_type]
        if column.nullable:
            ch_type = f"Nullable({ch_type})"
        line = f"  `{column.name}` {ch_type}"
        if column.comment:
            line += f" COMMENT '{_escape(column.comment)}'"
        lines.append(line)
    body = ",\n".join(lines)
    order_keys = table.primary_key or (table.columns[0].name,)
    order_by = ", ".join(f"`{key}`" for key in order_keys)
    comment = f"\nCOMMENT '{_escape(table.comment)}'" if table.comment else ""
    return (
        f"CREATE TABLE demo_shop.`{table.name}` (\n{body}\n) "
        f"ENGINE = MergeTree ORDER BY ({order_by}){comment};\n"
    )


def emit_clickhouse(data: dict[str, list[Row]], out_path: Path) -> None:
    """Write DDL + batched INSERTs for the ClickHouse docker init dir."""
    with out_path.open("w", encoding="utf-8") as f:
        f.write("-- Generated by generate_data.py; do not edit.\n")
        f.write("CREATE DATABASE IF NOT EXISTS demo_shop;\n\n")
        for table in TABLES:
            f.write(_clickhouse_ddl(table))
        f.write("\n")
        for table in TABLES:
            rows = data[table.name]
            col_list = ", ".join(f"`{c.name}`" for c in table.columns)
            for batch_start in range(0, len(rows), BATCH):
                batch = rows[batch_start : batch_start + BATCH]
                values = ",\n".join(
                    "(" + ", ".join(_sql_literal(v) for v in row) + ")" for row in batch
                )
                f.write(
                    f"INSERT INTO demo_shop.`{table.name}` ({col_list}) VALUES\n{values};\n"
                )


# --- SQLite emitter --------------------------------------------------------

SQLITE_TYPES = {
    "id": "INTEGER",
    "int": "INTEGER",
    "decimal": "REAL",
    "varchar": "TEXT",
    "datetime": "TEXT",  # ISO 'YYYY-MM-DD HH:MM:SS'; sqlite date() works on it
    "bool": "INTEGER",
}


def _sqlite_value(value: Value) -> int | float | str | None:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return value


def _sqlite_ddl(table: Table) -> str:
    lines = [
        f'  "{column.name}" {SQLITE_TYPES[column.ir_type]}'
        + ("" if column.nullable else " NOT NULL")
        for column in table.columns
    ]
    if table.primary_key:
        keys = ", ".join(f'"{k}"' for k in table.primary_key)
        lines.append(f"  PRIMARY KEY ({keys})")
    body = ",\n".join(lines)
    return f'CREATE TABLE "{table.name}" (\n{body}\n);'


def emit_sqlite(data: dict[str, list[Row]], db_path: Path) -> None:
    """Write the dataset as a single SQLite file (Docker-free demo path)."""
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    try:
        for table in TABLES:
            conn.execute(_sqlite_ddl(table))
            placeholders = ", ".join("?" for _ in table.columns)
            conn.executemany(
                f'INSERT INTO "{table.name}" VALUES ({placeholders})',
                (tuple(_sqlite_value(v) for v in row) for row in data[table.name]),
            )
        for table in TABLES:  # indexes after bulk insert: faster load
            for index in table.indexes:
                cols = ", ".join(f'"{c}"' for c in index)
                name = f"idx_{table.name}_{'_'.join(index)}"
                conn.execute(f'CREATE INDEX "{name}" ON "{table.name}" ({cols})')
        conn.commit()
    finally:
        conn.close()


def main() -> None:
    """Generate the dataset and emit MySQL init SQL + the SQLite file."""
    parser = argparse.ArgumentParser(description="Generate the demo_shop dataset")
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "initdb")
    parser.add_argument(
        "--sqlite-out", type=Path, default=Path(__file__).parent / "demo_shop.db"
    )
    args = parser.parse_args()
    rng = random.Random(SEED)
    now = datetime.now().replace(microsecond=0)
    data = generate(rng, now)
    print(
        f"users={len(data['users'])} orders={len(data['orders'])} "
        f"order_items={len(data['order_items'])}"
    )
    args.out.mkdir(parents=True, exist_ok=True)
    out_file = args.out / "10_demo_shop.sql"
    emit_mysql(data, out_file)
    print(f"wrote {out_file} ({out_file.stat().st_size / 1e6:.1f} MB)")
    emit_sqlite(data, args.sqlite_out)
    print(f"wrote {args.sqlite_out} ({args.sqlite_out.stat().st_size / 1e6:.1f} MB)")
    ch_dir = Path(__file__).parent / "initdb_clickhouse"
    ch_dir.mkdir(parents=True, exist_ok=True)
    ch_file = ch_dir / "10_demo_shop.sql"
    emit_clickhouse(data, ch_file)
    print(f"wrote {ch_file} ({ch_file.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
