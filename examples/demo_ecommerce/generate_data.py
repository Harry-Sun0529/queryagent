"""Generate the fictional ``demo_shop`` dataset (spec §五, AI-OWNED).

Rows are built in a dialect-agnostic intermediate representation (IR) and
handed to per-dialect emitters. v0.1.0 ships the MySQL emitter; v0.1.1 reuses
the same IR for the SQLite file (``demo_shop.db``) and, schedule permitting,
a ClickHouse replica.

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


def main() -> None:
    """Generate the dataset and emit the MySQL init script."""
    parser = argparse.ArgumentParser(description="Generate the demo_shop dataset")
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "initdb")
    args = parser.parse_args()
    rng = random.Random(SEED)
    now = datetime.now().replace(microsecond=0)
    data = generate(rng, now)
    args.out.mkdir(parents=True, exist_ok=True)
    out_file = args.out / "10_demo_shop.sql"
    emit_mysql(data, out_file)
    size_mb = out_file.stat().st_size / 1e6
    print(
        f"users={len(data['users'])} orders={len(data['orders'])} "
        f"order_items={len(data['order_items'])}"
    )
    print(f"wrote {out_file} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
