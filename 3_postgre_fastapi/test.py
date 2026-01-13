import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect(
        user="postgres",
        password="1234",
        database="Test",
        host="localhost",
        port=5432
    )
    print("CONNECTED")
    await conn.close()

asyncio.run(main())