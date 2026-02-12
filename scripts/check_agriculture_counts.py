"""Check Agriculture domain seed counts."""

import asyncio
import sys
from pathlib import Path

import sqlalchemy as sa

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.database import engine


async def main() -> None:
    async with engine.connect() as conn:
        root = await conn.execute(
            sa.text(
                "SELECT COUNT(*) FROM industries WHERE slug = 'agriculture-agritech'"
            )
        )
        subs = await conn.execute(
            sa.text(
                """
                SELECT COUNT(*)
                FROM industries
                WHERE parent_id IN (
                    SELECT id FROM industries WHERE slug = 'agriculture-agritech'
                )
                """
            )
        )
        entities = await conn.execute(
            sa.text(
                """
                SELECT COUNT(*)
                FROM entities
                WHERE industry_id IN (
                    SELECT id FROM industries WHERE slug = 'agriculture-agritech'
                    UNION
                    SELECT id FROM industries WHERE parent_id IN (
                        SELECT id FROM industries WHERE slug = 'agriculture-agritech'
                    )
                )
                """
            )
        )
        contracts = await conn.execute(
            sa.text(
                """
                SELECT COUNT(*)
                FROM signal_contracts
                WHERE industry_id IN (
                    SELECT id FROM industries WHERE slug = 'agriculture-agritech'
                    UNION
                    SELECT id FROM industries WHERE parent_id IN (
                        SELECT id FROM industries WHERE slug = 'agriculture-agritech'
                    )
                )
                """
            )
        )

        print(f"Agriculture root industries: {root.scalar()}")
        print(f"Agriculture sub-verticals: {subs.scalar()}")
        print(f"Agriculture entities: {entities.scalar()}")
        print(f"Agriculture signal contracts: {contracts.scalar()}")


if __name__ == "__main__":
    asyncio.run(main())
