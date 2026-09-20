import os
import sys
import asyncio
import discord
from discord.errors import Forbidden, HTTPException, NotFound

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = os.getenv("OBSERVER_CHANNEL_ID")


async def probe(message_id):
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        try:
            channel = await client.fetch_channel(int(CHANNEL_ID))
            message = await channel.fetch_message(int(message_id))

            print(f"API_RESULT=EXISTS")
            print(f"MESSAGE_ID={message.id}")
            print(f"CHANNEL_ID={message.channel.id}")
            print(f"AUTHOR_ID={message.author.id}")
            print(f"CREATED_AT={message.created_at.isoformat()}")
            print(f"CONTENT={message.content}")

        except NotFound:
            print("API_RESULT=NOT_FOUND")

        except Forbidden:
            print("API_RESULT=FORBIDDEN")

        except HTTPException as error:
            print("API_RESULT=HTTP_ERROR")
            print(f"HTTP_STATUS={error.status}")
            print(f"HTTP_CODE={error.code}")

        except Exception as error:
            print("API_RESULT=OTHER_ERROR")
            print(f"ERROR_TYPE={type(error).__name__}")
            print(f"ERROR={error}")

        finally:
            await client.close()

    await client.start(TOKEN)


async def main():
    if not TOKEN:
        raise RuntimeError("DISCORD_BOT_TOKEN is not configured")

    if not CHANNEL_ID:
        raise RuntimeError("OBSERVER_CHANNEL_ID is not configured")

    if len(sys.argv) != 2:
        print("Usage: python probe.py <message_id>")
        return

    await probe(sys.argv[1])


asyncio.run(main())
