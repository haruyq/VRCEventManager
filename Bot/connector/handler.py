import json
import aiohttp

from datetime import datetime, timedelta
from dateutil import tz

import discord
from discord.ext import commands

from utils.logger import Logger
from connector.responses import Responses

Log = Logger(__name__)

class RequestHandler:
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def parse_entity_type(self, entity_type_str: str) -> discord.EntityType:
        match entity_type_str.lower():
            case "stage_instance":
                return discord.EntityType.stage_instance
            case "voice":
                return discord.EntityType.voice
            case "external":
                return discord.EntityType.external
    
    def parse_isotime(self, start_time, end_time):
        """Parses and validates ISO 8601 time strings.
        Example:
            **input**
            * `start_time = "2025-10-03T07:30:00+09:00"`
            * `end_time = "2025-10-03T08:30:00+09:00"`

        Returns:
            tuple: A tuple containing the parsed start and end times.
        """
        start_time = (
            discord.utils.parse_time(start_time) if isinstance(start_time, str) else start_time
        ) or (datetime.now(tz=tz.tzlocal()) + timedelta(minutes=1))
        end_time = (
            discord.utils.parse_time(end_time) if isinstance(end_time, str) else end_time
        ) or (start_time + timedelta(hours=1))
        result = True
        if start_time <= datetime.now(tz=tz.tzlocal()):
            result = False
        if end_time <= start_time:
            end_time = start_time + timedelta(hours=1)
        Log.debug(f"Parsed times - Start: {start_time}, End: {end_time}, Result: {result}")

        return start_time, end_time, result

    async def handle(self, message): # Received JSON Handler
        try:
            data: dict = json.loads(message)
            Log.debug(f"Handling Data:\n {data}")
            action = data.get("action")
            
            match action:
                case "ping":
                    return Responses.ok("pong")

                case "send_announcement":
                    channel_id = data.get("channel_id")
                    everyone = data.get("everyone", False)
                    message = data.get("message")

                    if channel_id is None:
                        return Responses.error("channel_id is required")

                    channel = self.bot.get_channel(int(channel_id))
                    if channel is None:
                        channel = await self.bot.fetch_channel(int(channel_id))

                    if everyone:
                        allowed_mentions = discord.AllowedMentions(everyone=True)
                        message = f"@everyone\n {message}"
                    else:
                        allowed_mentions = discord.AllowedMentions.none()

                    msg = await channel.send(message, allowed_mentions=allowed_mentions)
                    return Responses.ok(f"Announcement sent with ID {msg.id}")
                
                case "create_event":
                    guild_id = int(data.get("guild_id"))
                    channel_id = data.get("channel_id", None)
                    name = data.get("name")
                    description = data.get("description")
                    start_time = data.get("start_time", None)
                    end_time = data.get("end_time", None)
                    entity_type = self.parse_entity_type(data.get("entity_type"))
                    location = data.get("location")
                    image_uri = data.get("image_uri", None)
                    
                    # if entity_type is not external, it must be set a channel
                    # and location must be MISSING
                    if channel_id is not None and entity_type in (
                        discord.EntityType.stage_instance,
                        discord.EntityType.voice
                    ):
                        channel = self.bot.get_channel(int(channel_id))
                        if channel is None:
                            channel = await self.bot.fetch_channel(int(channel_id))
                            location = discord.utils.MISSING
                        
                        if not channel or not isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
                            return Responses.error("Invalid channel for the specified entity type")
                    elif channel_id is None and entity_type in (discord.EntityType.stage_instance, discord.EntityType.voice):
                        return Responses.error("channel_id is required for the specified entity type")
                    else:
                        channel = discord.utils.MISSING
                    
                    # Download image and encode to bytes if provided
                    if image_uri is not None:
                        async with aiohttp.ClientSession() as session:
                            async with session.get(image_uri) as resp:
                                if resp.status != 200:
                                    return Responses.error("Failed to fetch image from URI")
                                image_bytes = await resp.read()
                    else:
                        image_bytes = discord.utils.MISSING
                    
                    try:
                        guild = self.bot.get_guild(guild_id)
                        if guild is None:
                            guild = await self.bot.fetch_guild(guild_id)
                        
                        if not guild:
                            return Responses.error("Guild not found")
                        
                        start_time, end_time, result = self.parse_isotime(start_time, end_time)
                        if not result:
                            return Responses.error("Invalid start_time; must be in the future")
                        
                        kwargs = {
                            "name": name,
                            "start_time": start_time,
                            "end_time": end_time,
                            "entity_type": entity_type,
                            "privacy_level": discord.PrivacyLevel.guild_only,
                            "description": description,
                            "image": image_bytes,
                            "reason": "Created via VRCEventManager",
                        }
                        if entity_type in (discord.EntityType.stage_instance, discord.EntityType.voice):
                            kwargs["channel"] = channel
                        else:
                            kwargs["location"] = location

                        event = await guild.create_scheduled_event(**kwargs)
                        return Responses.ok(f"Event {name} created with ID {event.id}")
                    
                    except Exception as e:
                        Log.error(f"Failed to create event: {e}", exc_info=True)
                        return Responses.error(f"Failed to create event: {e}")

                case "check_admin":
                    user_id = int(data.get("user_id"))
                    guild_id = int(data.get("guild_id"))
                    
                    guild = self.bot.get_guild(guild_id)
                    if guild is None:
                        guild = await self.bot.fetch_guild(guild_id)
                    
                    if not guild:
                        return Responses.error("Guild not found")
                    
                    member = guild.get_member(user_id)
                    if member is None:
                        member = await guild.fetch_member(user_id)
                    
                    if not member:
                        return Responses.error("Member not found")
                    
                    is_admin = any(role.permissions.administrator for role in member.roles)
                    return Responses.ok({"is_admin": is_admin})

                case _:
                    return Responses.error("Unknown action")

        except json.JSONDecodeError:
            return Responses.error("Invalid JSON")