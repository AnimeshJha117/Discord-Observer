import os
import asyncio
import json
from datetime import datetime, timezone

import discord
from discord.errors import Forbidden, HTTPException, NotFound

token = os.getenv("DISCORD_BOT_TOKEN")
channel_id = os.getenv("OBSERVER_CHANNEL_ID")

if token is None:
    raise RuntimeError("DISCORD_BOT_TOKEN is not configured")

if channel_id is None:
    raise RuntimeError("OBSERVER_CHANNEL_ID is not configured")

try:
    channel_id = int(channel_id)
except ValueError:
    raise RuntimeError("OBSERVER_CHANNEL_ID must be a number.")

log_file = "event_log.jsonl"

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents = intents)

def write_event(event):
    with open(log_file, "a", encoding =  "utf-8") as file:
        json.dump(event, file, ensure_ascii = False)
        file.write("\n")

def now_utc():
    return datetime.now(timezone.utc).isoformat()

@client.event
async def on_ready():
    event = {
        "event" : "OBSERVER_READY",
        "observed_at" : now_utc(),
    }

    write_event(event)
    print(f"Logged in as {client.user}")
    print("Witnyas is connected.")
    print(f"Witnessing channel: {channel_id}")
    print(f"Writing events to: {log_file}")

@client.event
async def on_disconnect():
    event = {
        "event": "OBSERVER_DISCONNECT",
        "observed_at": now_utc(),
    }

    write_event(event)
    print("Discord Gateway disconnected.")

@client.event
async def on_message(message):
    if message.channel.id != channel_id:
        return

    event = {
        "event" : "MESSAGE_CREATE",
        "observed_at" : now_utc(),
        "message_id" : message.id,
        "channel_id" : message.channel.id,
        "guild_id" : message.guild.id if message.guild else None,
        "author_id" : message.author.id,
        "timestamp" : message.created_at.astimezone(timezone.utc).isoformat(),
        "content" : message.content,
    }

    write_event(event)
    print(json.dumps(event, ensure_ascii = False))

@client.event
async def on_raw_message_delete(payload):
    if payload.channel_id != channel_id:
        return

    print(f"MESSAGE_DELETE received: {payload.message_id}")

    event = {
        "event" : "MESSAGE_DELETE",
        "observed_at" : now_utc(),
        "message_id" : payload.message_id,
        "channel_id" : payload.channel_id,
    }

    channel = client.get_channel(payload.channel_id)

    if channel is None:
        event["api_result"] = "CHANNEL_NOT_CACHED"
        print("API lookup: CHANNEL_NOT_CACHED")
        write_event(event)
        return

    try:
        message = await channel.fetch_message(payload.message_id)

        event["api_result"] = "EXISTS"
        event["api_message_id"] = message.id

        print(f"API lookup: EXISTS "
            f"(message {message.id} is still retrievable)")

    except NotFound:
        event["api_result"] = "NOT_FOUND"
        print("API lookup: NOT_FOUND")

    except Forbidden:
        event["api_result"] = "FORBIDDEN"
        print("API lookup: FORBIDDEN")

    except HTTPException as error:
        event["api_result"] = "HTTP_ERROR"
        event["http_status"] = error.status
        event["http_code"] = error.code

        print(f"API lookup: HTTP_ERROR "
            f"(status={error.status}, code={error.code})")

    except Exception as error:
        event["api_result"] = "OTHER_ERROR"
        event["error_type"] = type(error).__name__
        event["error_message"] = str(error)

        print(f"API lookup: OTHER_ERROR "
            f"({type(error).__name__}: {error})")

    write_event(event)

@client.event
async def on_raw_message_edit(payload):
    if payload.channel_id != channel_id:
        return

    event = {
        "event" : "MESSAGE_EDIT",
        "observed_at" : now_utc(),
        "message_id" : payload.message_id,
        "channel_id" : payload.channel_id,
    }

    if payload.data:
        event["data"] = payload.data

    write_event(event)
    print(f"MESSAGE_EDIT received: {payload.message_id}")

async def api_probe():
    while True:
        command = await asyncio.to_thread(input, "observer> ")

        parts = command.strip().split()

        if len(parts) != 2 or parts[0].lower() != "check":
            print("Usage: check <message_id>")
            continue

        try:
            message_id = int(parts[1])

        except ValueError:
            print("Message ID must be a number.")
            continue

        channel = client.get_channel(channel_id)

        if channel is None:
            print("API probe: CHANNEL_NOT_CACHED")
            continue

        event = {
            "event": "API_PROBE",
            "observed_at": now_utc(),
            "message_id": message_id,
            "channel_id": channel_id,
        }

        try:
            message = await channel.fetch_message(message_id)
            event["api_result"] = "EXISTS"
            print(f"API probe: EXISTS "
                f"(message {message.id} is retrievable)")

        except NotFound:
            event["api_result"] = "NOT_FOUND"
            print("API probe: NOT_FOUND")

        except Forbidden:
            event["api_result"] = "FORBIDDEN"
            print("API probe: FORBIDDEN")

        except HTTPException as error:
            event["api_result"] = "HTTP_ERROR"
            event["http_status"] = error.status
            event["http_code"] = error.code

            print(f"API probe: HTTP_ERROR "
                f"(status={error.status}, code={error.code})")

        except Exception as error:
            event["api_result"] = "OTHER_ERROR"
            event["error_type"] = type(error).__name__
            event["error_message"] = str(error)

            print(f"API probe: OTHER_ERROR "
                f"({type(error).__name__}: {error})")

        write_event(event)

async def main():
    asyncio.create_task(api_probe())
    await client.start(token)

asyncio.run(main())