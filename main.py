import discord
import os
import json
import random
from discord.ext import commands
from datetime import datetime, timedelta

# Create a file to store user data
DATA_FILE = "data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as file:
                return json.load(file)
        except json.JSONDecodeError:
            print("Error decoding data.json! Resetting file.")
            return {}
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as file:
        json.dump(data, file, indent=4)

# Load data from the file
user_data = load_data()

# Initialize bot with intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents, case_insensitive=True)
COOLDOWN_TIME = timedelta(hours=1)
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}!")
    try:
        synced = await bot.tree.sync()
        print(f"Successfully synced {len(synced)} slash commands!")
    except Exception as e:
        print(f"Error syncing commands: {e}")

# Ensure user has an account
def ensure_account(user_id):
    if str(user_id) not in user_data:
        user_data[str(user_id)] = {"balance": 1000, "last_daily_claim": None, "last_work": None, "last_rps": None, "last_gamble": None}
        save_data(user_data)
# Work
@bot.tree.command(name="work", description="Earn coins by working.")
async def slash_work(interaction: discord.Interaction):
    ensure_account(interaction.user.id)
    earnings = random.randint(100, 300)
    user_data[str(interaction.user.id)]["balance"] += earnings

    save_data(user_data)

    await interaction.response.send_message(f"{interaction.user.mention}, you worked and earned {earnings} coins!")
#Daily
@bot.tree.command(name="daily", description="Claim your daily reward!")
async def slash_daily(interaction: discord.Interaction):
    ensure_account(interaction.user.id)

    user = user_data[str(interaction.user.id)]
    now = datetime.utcnow()
    last_claim = user.get("last_daily_claim", None)

    if last_claim:
        # Parse the last claim time from string
        last_claim_time = datetime.strptime(last_claim, "%Y-%m-%d %H:%M:%S")
    else:
        last_claim_time = None

    # Check if the user can claim again
    if last_claim_time and now - last_claim_time < timedelta(days=1):
        remaining_time = last_claim_time + timedelta(days=1) - now
        hours, remainder = divmod(remaining_time.seconds, 3600)
        minutes = remainder // 60
        await interaction.response.send_message(
            f"{interaction.user.mention}, you can claim your daily reward again in {remaining_time.days} days, {hours} hours, and {minutes} minutes."
        )
    else:
        # Grant the reward
        reward = random.randint(100, 400)
        user["balance"] += reward
        user["last_daily_claim"] = now.strftime("%Y-%m-%d %H:%M:%S")
        save_data(user_data)
        await interaction.response.send_message(
            f"{interaction.user.mention}, you claimed your daily reward of {reward} coins!"
        )
# Gamble command
bot.tree.command(name="gamble", description="Gamble a certain amount of coins.")
async def slash_gamble(interaction: discord.Interaction, amount: int):
    ensure_account(interaction.user.id)
    user = user_data[str(interaction.user.id)]
    if amount < 1 or amount > 1000:
        await interaction.response.send_message(
            f"You can only gamble between 1 and 1000 coins.", ephemeral=True
        )
        return
    if amount > user["balance"]:
        await interaction.response.send_message(
            f"You don't have enough coins to gamble.", ephemeral=True
        )
        return

    # Simulate gambling
    result = random.choice(["win", "lose"])
    if result == "win":
        user["balance"] += amount
    else:
        user["balance"] -= amount

    # Save the updated data
    save_data(user_data)

    # Respond to the user
    await interaction.response.send_message(
        f"You **{result}**! Your new balance is **{user['balance']} coins**."
    )

# Rock Paper Scissors
@bot.tree.command(name="rps", description="Play Rock, Paper, Scissors to earn coins.")
async def slash_rps(interaction: discord.Interaction, wager: int, choice: str):
    ensure_account(interaction.user.id)
    user = user_data[str(interaction.user.id)]
    choice = choice.lower()
    if wager < 1:
        await interaction.response.send_message(f"{interaction.user.mention}, you must wager at least 1 coin.")
        return
    if wager > user["balance"]:
        await interaction.response.send_message(f"{interaction.user.mention}, you don't have enough coins to wager.")
        return
    valid_choices = ["rock", "paper", "scissors"]
    if choice not in valid_choices:
        await interaction.response.send_message(
            f"{interaction.user.mention}, your choice must be one of: rock, paper, or scissors."
        )
        return
    bot_choice = random.choice(valid_choices)

    # Determine the winner
    outcomes = {
        ("rock", "scissors"): "win",
        ("scissors", "paper"): "win",
        ("paper", "rock"): "win",
        ("scissors", "rock"): "lose",
        ("paper", "scissors"): "lose",
        ("rock", "paper"): "lose",
    }
    if choice == bot_choice:
        result = "draw"
    else:
        result = outcomes.get((choice, bot_choice), "lose")

    # Adjust balance based on the result
    if result == "win":
        winnings = wager * 2  # User wins double their wager
        user["balance"] += winnings
        save_data(user_data)
        await interaction.response.send_message(
            f"{interaction.user.mention}, you chose **{choice}**, and I chose **{bot_choice}**. You **won** {winnings} coins! Your new balance is {user['balance']}."
        )
    elif result == "lose":
        user["balance"] -= wager
        save_data(user_data)
        await interaction.response.send_message(
            f"{interaction.user.mention}, you chose **{choice}**, and I chose **{bot_choice}**. You **lost** {wager} coins. Your new balance is {user['balance']}."
        )
    else:  # Draw
        await interaction.response.send_message(
            f"{interaction.user.mention}, you chose **{choice}**, and I chose **{bot_choice}**. It's a **draw**! No coins were exchanged."
        )

# Leaderboard Slash Command
@bot.tree.command(name="leaderboard", description="View the top players.")
async def slash_leaderboard(interaction: discord.Interaction):
    leaderboard = sorted(user_data.items(), key=lambda x: x[1]["balance"], reverse=True)
    message = "**Leaderboard**\n"
    for i, (user_id, data) in enumerate(leaderboard[:10], start=1):
        user = await bot.fetch_user(int(user_id))
        message += f"{i}. {user.name} - {data['balance']} coins\n"
    await interaction.response.send_message(message)

# Command: View Store
@bot.tree.command(name="store", description="View items available in the store.")
async def slash_store(interaction: discord.Interaction):
    store_items= [
        {"id": 3213, "name": "Cheese", "price": 100, "description": "A delicious snack."},
        {"id": 5631, "name": "Snoopy", "price": 700, "description": "A cute plush toy."},
        {"id": 7675, "name": "Miffy", "price": 1500, "description": "A lovable bunny."},
        {"id": 5414, "name": "Kiiroitori", "price": 2300, "description": "A cute yellow bird."},
        {"id": 6573, "name": "Rilakumma", "price": 3500, "description": "A lazy bear."},
        {"id": 8093, "name": "Korilakkuma", "price": 5000, "description": "A mischievous bear."}
    ]
    message = "**Store Items**\n"
    for item in store_items:
        message += f"**{item['name'].capitalize()}**: {item['price']} coins\n{item['description']}\n\n"
    await interaction.response.send_message(message)

# Command: Buy Item
@bot.tree.command(name="buy", description="Buy an item from the store.")
async def slash_buy(interaction: discord.Interaction, item_name: str):
    ensure_account(interaction.user.id)
    user = user_data[str(interaction.user.id)]
    
    store_items= [
        {"id": 3213, "name": "Cheese", "price": 100},
        {"id": 5631, "name": "Snoopy", "price": 700},
        {"id": 7675, "name": "Miffy", "price": 1500,},
        {"id": 5414, "name": "Kiiroitori", "price": 2300},
        {"id": 6573, "name": "Rilakumma", "price": 3500},
        {"id": 8093, "name": "Korilakkuma", "price": 5000}
    ] 
    item_name = item_name.lower()

# Double-check user balance
    if user["balance"] < store_items["price"]:
        await interaction.response.send_message(f"{interaction.user.mention}, you don't have enough coins to buy {item_name}.")
        return

    # Purchase the item
    user["balance"] -= store_items["price"]

    # Add item to inventory
    if item_name in user["inventory"]:
        user["inventory"][item_name] += 1
    else:
        user["inventory"][item_name] = 1

    # Save user data after purchase
    try:
        save_data(user_data)
    except Exception as e:
        await interaction.response.send_message(f"An error occurred while saving your data: {e}. Please try again later.")
        return

    await interaction.response.send_message(f"{interaction.user.mention}, you bought a {item_name}! Your new balance is {user['balance']} coins.")

# View Inventory Command
@bot.tree.command(name="inventory", description="View your inventory.")
async def slash_inventory(interaction: discord.Interaction):
    ensure_account(interaction.user.id)
    user = user_data[str(interaction.user.id)]
    inventory = user["inventory"]

    if not inventory:
        await interaction.response.send_message(f"{interaction.user.mention}, your inventory is empty.")
        return

    message = "**Your Inventory**\n"
    for item, quantity in inventory.items():
        message += f"{item.capitalize()}: {quantity}\n"
    await interaction.response.send_message(message)

# Optional Text 
@bot.command()
async def balance(ctx):
    ensure_account(ctx.author.id)
    balance = user_data[str(ctx.author.id)]["balance"]
    await ctx.send(f"{ctx.author.mention}, you have {balance} coins.")
#Extra
@bot.command()
async def work(ctx):
    ensure_account(ctx.author.id)
    earnings = random.randint(100, 300)
    user_data[str(ctx.author.id)]["balance"] += earnings
    save_data(user_data)
    await ctx.send(f"{ctx.author.mention}, you worked and earned {earnings} coins!")

bot.run('MTMxMjE4MDA1MTg2OTE3MTcyMg.GnLnQd.qy2hP6Ou2frcWQgt4PnbxCfpKIhqZQJsWXLXjU')