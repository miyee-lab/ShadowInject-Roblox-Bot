import requests
import discord
import time
from discord.ext import tasks, commands
import json
from datetime import date
from discord.utils import get
from discord.ext.commands import check, MissingRole, CommandError

# --- Discord Bot Configuration ---
intents = discord.Intents.all()

try:
    with open("config.json", "r") as f:
        bot_config = json.load(f)
except FileNotFoundError:
    print("[ERROR] config.json not found. Please ensure the file exists in the same directory.")
    exit()
except json.JSONDecodeError:
    print("[ERROR] Error decoding config.json. Please check the JSON format.")
    exit()

client = commands.Bot(command_prefix=bot_config["bot_prefix"], intents=intents)

try:
    POST_CHANNEL = bot_config["channelId"]
    PING_ROLE_ID = bot_config["pingRoleId"]
except KeyError as e:
    print(f"[ERROR] Missing configuration key in config.json: {e}. Please ensure 'channelId' and 'pingRoleId' are set.")
    exit()

# --- API Endpoints ---
ROBLOX_VERSION_API = 'https://whatexpsare.online/api/versions/current'

# File to store the last known Roblox version DATE to avoid duplicate notifications
LAST_VERSION_DATE_FILENAME = "last_roblox_version_date.txt"

@client.event
async def on_ready():
    """Event handler for when the bot successfully connects to Discord."""
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Roblox Tracker"))
    print('<---------------- NEW SESSION ----------------->')
    print('[SUCCESS] : Logged in as ' + format(client.user))
    print('------------------------------------------------\n\n')
    roblox_version_checker.start()

@client.command(pass_context=True)
async def ping(ctx):
    """Command to check bot's latency."""
    await ctx.send(f"> `Pong! {round(client.latency * 1000)}ms`")

@client.command(pass_context=True)
async def status(ctx):
    """Command to check roblox version."""
    await ctx.send(f"> `roblox version {ROBLOX_VERSION_API}`")

# --- Roblox Version Monitoring Task ---
@tasks.loop(seconds=100)  # Check every 1 minutes (100 seconds)
async def roblox_version_checker():
    """
    Periodically checks the Roblox version API for Windows version and date,
    and notifies a Discord channel if the date has changed.
    """
    try:
        # --- Fetch New Roblox Version Data ---
        print(f"[INFO] Fetching current Roblox version data from: {ROBLOX_VERSION_API}")
        new_version_response = requests.get(ROBLOX_VERSION_API)
        new_version_response.raise_for_status()
        new_version_data = new_version_response.json()

        # Extract Windows version and date
        new_roblox_version = new_version_data.get('Windows')
        new_roblox_date = new_version_data.get('WindowsDate')

        if not new_roblox_version or not new_roblox_date:
            print("[ERROR] Failed to retrieve Windows version or date from the API response.")
            return

        print(f"[INFO] Successfully fetched: Version={new_roblox_version}, Date={new_roblox_date}")

        # --- Read Last Known Version Date ---
        last_known_date = ""
        try:
            with open(LAST_VERSION_DATE_FILENAME, "r") as f:
                last_known_date = f.read().strip()
            print(f"[INFO] Last known Roblox version date: '{last_known_date}'" if last_known_date else "[INFO] No previous Roblox version date found.")
        except FileNotFoundError:
            print("[INFO] No previous Roblox version date file found. This is the first check.")
        except Exception as e:
            print(f"[ERROR] Failed to read last known version date file: {e}")

        # --- Compare Dates and Notify ---
        if new_roblox_date != last_known_date:
            print(f"[SUCCESS] New RobloxGameClient version date detected!")
            print(f"  New Date: {new_roblox_date}")

            # Get the Discord channel and send an embed message
            channel = client.get_channel(POST_CHANNEL)
            if channel:
                embed = discord.Embed(
                    title="RobloxGameClient Update",
                    description=f"RobloxGameClient has been updated!",
                    color=0x43B581
                )
                embed.add_field(name="Platform", value=f"```\nWindows\n```", inline=False)
                embed.add_field(name="Version", value=f"```\n{new_roblox_version}\n```", inline=False)
                embed.add_field(name="Version Date", value=f"```\n{new_roblox_date}\n```", inline=False)

                guild = channel.guild
                role_to_ping = guild.get_role(PING_ROLE_ID)

                if role_to_ping:
                    # --- POPRAWKA DOTYCZĄCA F-STRINGA ---
                    await channel.send(f"{role_to_ping.mention}\nRobloxGameClient has been updated!", embed=embed)
                    print(f"[INFO] Sent update notification with ping to role '{role_to_ping.name}' in channel ID: {POST_CHANNEL}")
                else:
                    print(f"[ERROR] Could not find role with ID: {PING_ROLE_ID}. Please check 'pingRoleId' in config.json.")
                    await channel.send(embed=embed)
                    print(f"[INFO] Sent update notification without ping to channel ID: {POST_CHANNEL}")
            else:
                print(f"[ERROR] Could not find channel with ID: {POST_CHANNEL}. Please check POST_CHANNEL in config.json.")

            # --- Save the New Version Date ---
            try:
                with open(LAST_VERSION_DATE_FILENAME, "w") as f:
                    f.write(new_roblox_date)
                print(f"[INFO] Saved new version date '{new_roblox_date}' to {LAST_VERSION_DATE_FILENAME}")
            except Exception as e:
                print(f"[ERROR] Failed to save new Roblox version date to file: {e}")

        else:
            print("[INFO] RobloxGameClient version date has not changed.")

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] An error occurred while fetching data from the API: {e}")
    except json.JSONDecodeError:
        print("[ERROR] Failed to decode JSON response from the API. The API might be returning invalid JSON.")
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred: {e}")


@roblox_version_checker.before_loop
async def before_roblox_version_checker():
    """Ensures the bot is ready before starting the version checking loop."""
    await client.wait_until_ready()
    print("Starting Roblox version checker loop...")


# --- Run the Bot ---
try:
    client.run(bot_config["bot_token"])
except discord.errors.LoginFailure:
    print("[ERROR] Invalid bot token. Please check your 'bot_token' in config.json.")
except KeyError as e:
    print(f"[ERROR] Missing configuration key in config.json: {e}. Ensure 'bot_prefix', 'channelId', and 'bot_token' are set.")
except Exception as e:
    print(f"[ERROR] An unexpected error occurred during bot startup: {e}")
