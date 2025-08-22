import os
import logging
import discord
import uuid
from discord.ext import commands
from discord.ui import View,Button,Modal,TextInput
from discord import app_commands
from dotenv import load_dotenv
from discord.ui import View, Select

load_dotenv()
TICKET_DATA={}
TOKEN = os.getenv("DISCORD_TOKEN")
STAFF_ROLE_ID = int(os.getenv("STAFF_ROLE_ID"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("taskflow-bot")

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

@bot.event
async def on_ready():
    logger.info(f"Bot connected as {bot.user} (ID: {bot.user.id})")
    logger.info(f"Connected to {len(bot.guilds)} guild(s): {[g.name for g in bot.guilds]}")
    
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} command(s)")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")

@bot.tree.command(name="ping", description="Check if the bot is responsive.")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")

@bot.command(name="ping", help="Check if the bot is responsive.")
async def ping_message(ctx: commands.Context):
    await ctx.send("Pong!")

class BoardSelect(View):
    def __init__(self,categories, reason=None):
        super().__init__()
        self.reason = reason
        options=[discord.SelectOption(label=cat.name) for cat in categories]
        self.add_item(discord.ui.Select(
            placeholder="Choose a board...",
            options=options,
            custom_id="board_select"
        ))
    
    @discord.ui.select(custom_id="board_select")
    async def select_callback(self, select, interaction: discord.Interaction):
        board_name=select.values[0]
        guild=interaction.guild
        category_channel = discord.utils.get(guild.categories, name=board_name)

        ticket_name = f"ticket-{interaction.user.name}-{str(uuid.uuid4())[:8]}".lower()

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        staff_role = guild.get_role(STAFF_ROLE_ID)
        overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        ticket_channel = await guild.create_text_channel(
            name=ticket_name,
            category=category_channel,
            overwrites=overwrites
        )

        TICKET_DATA[ticket_channel.id] = {
            "category": board_name,
            "assigned_to": [],
            "deadline": None,
            "checklist": [],         
            "task_title": None
        } 

        await ticket_channel.send(f"Hello {interaction.user.mention}, will assist you shortly.\n"
            f"Reason: {self.reason if self.reason else 'No reason provided.'}")
        await interaction.response.send_message(f"Your ticket has been created: {ticket_channel.mention}", ephemeral=True)

@bot.tree.command(name="ticket", description="Create a new support ticket.")
@app_commands.describe(reason="Reason for opening the ticket",board="Board/Category to place the ticket in")
async def ticket_slash(interaction: discord.Interaction, reason: str = None, board: str=None):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
   
    if board:
       category_channel = discord.utils.get(guild.categories, name=board)
       if not category_channel:
        return await interaction.followup.send(f"No board named **{board}** found.", ephemeral=True) 
       ticket_name = f"ticket-{interaction.user.name}-{str(uuid.uuid4())[:8]}".lower()
       overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
       }
       staff_role = guild.get_role(STAFF_ROLE_ID)
       overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
       ticket_channel = await guild.create_text_channel(
        name=ticket_name,
        category=category_channel,
        overwrites=overwrites
       )
       TICKET_DATA[ticket_channel.id]={
        "category":board if board else category_channel.name,
        "assigned_to":[],
        "deadline":None,
        "checklist":[],
        "task_title": None
    }
       await ticket_channel.send(
        f"Hello {interaction.user.mention}, will assist you shortly.\n"
        f"Reason: {reason if reason else 'No reason provided.'}"
       )
       await interaction.followup.send(f"Your ticket has been created: {ticket_channel.mention}", ephemeral=True)
    else:
        categories=[c for c in guild.categories]
        view= BoardSelect(categories, reason=reason)
        await interaction.followup.send("Select a board for your ticket:", view=view, ephemeral=True)
 
@bot.tree.command(name="close", description="Close the current ticket (staff only).")
async def close_slash(interaction: discord.Interaction):
    if STAFF_ROLE_ID not in [role.id for role in interaction.user.roles]:
     await interaction.response.send_message("You don’t have permission to close tickets.", ephemeral=True)
     return
    if interaction.channel.name.startswith("ticket-"):
        await interaction.channel.delete()
    else:
        await interaction.response.send_message("This command can only be used in a ticket channel.", ephemeral=True)

@bot.tree.command(name="assign",description="Assign one or more user to this ticket.")
@app_commands.describe(member="Members to assign to the ticket")
async def assign_slash(interaction: discord.Interaction, member: discord.Member):
    if not interaction.channel.name.startswith("ticket-"):
        return await interaction.response.send_message("This command can only be used in a ticket channel.", ephemeral=True)
    ticket= TICKET_DATA.setdefault(interaction.channel.id, {})
    assigned_list=ticket.setdefault("assigned_to",[])
    if member.id not in assigned_list:
      assigned_list.append(member.id)
      await interaction.response.send_message(f"Added {member.mention} to the ticket.")
    else:   
      await interaction.response.send_message(f"{member.mention} is already assigned.", ephemeral=True) 

@bot.tree.command(name="deadline", description="Set a deadline for this ticket.")
@app_commands.describe(date="Deadline in YYYY-MM-DD format")
async def deadline_slash(interaction: discord.Interaction,date: str):
    if not interaction.channel.name.startswith("ticket-"):
        return await interaction.response.send_message("This command can only be used in a ticket channel.", ephemeral=True)
    TICKET_DATA.setdefault(interaction.channel.id,{})["deadline"] = date
    await interaction.response.send_message(f"Deadline set to {date}.")

@bot.tree.command(name="setcategory", description="Set or change the board for this ticket.")
async def setcategory_slash(interaction: discord.Interaction):
    await interaction.response.send_modal(CategoryModal())

@bot.tree.command(name="info", description="Get info about this ticket.")
async def info_slash(interaction: discord.Interaction):
    if not interaction.channel.name.startswith("ticket-"):
        return await interaction.response.send_message("This command can only be used in a ticket channel.", ephemeral=True)
    data = TICKET_DATA.get(interaction.channel.id)
    if not data:
        return await interaction.response.send_message("No data found for this ticket.", ephemeral=True)
    assigned = ", ".join(f"<@{uid}>" for uid in data.get('assigned_to', [])) or "Unassigned"
    deadline = data.get("deadline", "None")
    category = data.get("category", "None")
    embed = discord.Embed(title="Ticket Info")
    embed.add_field(name="Assigned To", value=assigned, inline=False)
    embed.add_field(name="Deadline", value=deadline, inline=False)
    embed.add_field(name="Category", value=category, inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)
    
class TicketDashboard(discord.ui.View):
    def __init__(self):
        super().__init__()
    @discord.ui.button(label="Set Deadline", style=discord.ButtonStyle.green)
    async def set_deadline(self, interaction: discord.Interaction, button:discord.ui.Button):
         modal = DeadlineModal()
         await interaction.response.send_modal(modal)
    @discord.ui.button(label="Assign Member", style=discord.ButtonStyle.blurple)
    async def assign_member(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = AssignModal()
        await interaction.response.send_modal(modal)
    @discord.ui.button(label="Set Category", style=discord.ButtonStyle.gray)
    async def set_category(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = CategoryModal()
        await interaction.response.send_modal(modal)

class DeadlineModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Set Ticket Deadline")
        self.deadline= discord.ui.TextInput(label="Deadline (YYYY-MM-DD)", placeholder="2025-08-20")
        self.add_item(self.deadline)
    async def on_submit(self, interaction: discord.Interaction):
        ticket=TICKET_DATA.get(interaction.channel.id)
        if ticket:
            ticket["deadline"] =self.deadline.value
            await interaction.response.send_message(f"Deadline updated to {self.deadline.value}", ephemeral=True)
        else:
            await interaction.response.send_message("Ticket not found.", ephemeral=True)

class AssignModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Assign Member to Ticket")
        self.member_input = discord.ui.TextInput(
            label="Member", 
            placeholder="Mention the member like @username or type their name"
        )
        self.add_item(self.member_input)

    async def on_submit(self, interaction: discord.Interaction):
        ticket = TICKET_DATA.get(interaction.channel.id)
        if not ticket:
            return await interaction.response.send_message("Ticket not found.", ephemeral=True)

        input_value = self.member_input.value.strip()
        member = None

        if input_value.startswith("<@") and input_value.endswith(">"):
            member_id = int(input_value.replace("<@", "").replace("!", "").replace(">", ""))
            member = interaction.guild.get_member(member_id)

        elif "#" in input_value:
            name, discrim = input_value.split("#")
            member = discord.utils.get(interaction.guild.members, name=name, discriminator=discrim)

        else:
            member = discord.utils.get(interaction.guild.members, name=input_value)

        if not member:
            return await interaction.response.send_message(
                f"Could not find a member matching '{input_value}'.", ephemeral=True
            )

        assigned_list = ticket.setdefault("assigned_to", [])
        if member.id not in assigned_list:
            assigned_list.append(member.id)
            await interaction.response.send_message(
                f"{member.mention} assigned to the ticket.", ephemeral=True
            )
        else:
            await interaction.response.send_message("Member is already assigned.", ephemeral=True)

class CategoryModal(discord.ui.Modal, title="Set Ticket Category"):
    category = discord.ui.TextInput(
        label="Enter new category name",
        placeholder="eg. Frontend, Backend, Design",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        new_category = self.category.value  
        
        category_obj = discord.utils.get(interaction.guild.categories, name=new_category)
        if not category_obj:
            return await interaction.response.send_message(f"Category '{new_category}' not found in the server.",ephemeral=True)
        await interaction.channel.edit(category=category_obj)

        ticket = TICKET_DATA.get(interaction.channel.id)
        if ticket:
            ticket["category"] = new_category
        else:
            TICKET_DATA[interaction.channel.id] = {"category": new_category}

        await interaction.response.send_message(f"Category successfully changed to **{new_category}**.",ephemeral=True)

@bot.tree.command(name="task", description="Create a new task (checklist container).")
@app_commands.describe(title="Title of the task")
async def task_create(interaction: discord.Interaction,title: str):
    if not interaction.channel.name.startswith("ticket-"):
        return await interaction.response.send_message("This command can only be used in a ticket channel.", ephemeral=True)

    ticket = TICKET_DATA.setdefault(interaction.channel.id, {
        "category": None,
        "assigned_to": [],
        "deadline": None,
        "checklist": [],
    })
    
    if "task_title" in ticket and ticket["task_title"]:
      return await interaction.response.send_message("A task already exists for this ticket.", ephemeral=True)
    ticket["checklist"] = []
    ticket["task_title"] = title

    ticket["task_title"]=title
    await interaction.response.send_message(f"✅ Task **{title}** created.Add items to it.", ephemeral=True)

@bot.tree.command(name="checklist_add",description="Add an item to the checklist.")
@app_commands.describe(item="Checklist item text")
async def checklist_add(interaction: discord.Interaction, item: str):
    if not interaction.channel.name.startswith("ticket-"):
      return await interaction.response.send_message("This command can only be passed in a ticket channel.", ephemeral=True)
    
    ticket=TICKET_DATA.get(interaction.channel.id)
    if not ticket or "checklist" not in ticket:
        return await interaction.response.send_message("No task exists for this ticket. Use /task first.", ephemeral=True)
    
    ticket["checklist"].append({"text": item, "done": False})
    await interaction.response.send_message(f"➕ Added checklist item: **{item}**", ephemeral=True)

@bot.tree.command(name="checklist_update", description="Update the status of a checklist item.")
@app_commands.describe(index="Item number(starting from 1)",status="done or pending")
async def checklist_update(interaction:discord.Interaction, index: int, status: str):
    if not interaction.channel.name.startswith("ticket-"):
        return await interaction.response.send_message("This command can only be used in a ticket channel.", ephemeral=True)
      
    ticket= TICKET_DATA.get(interaction.channel.id)
    if not ticket or "checklist" not in ticket:
         return await interaction.response.send_message("No checklist exists for this ticket.", ephemeral=True)
    
    if status.lower() not in ["done", "pending"]:
      return await interaction.response.send_message("Status must be 'done' or 'pending'.", ephemeral=True)

    checklist=ticket["checklist"]
    if index < 1 or index > len(checklist):
      return await interaction.response.send_message("Invalid item index.", ephemeral=True)
    
    checklist[index-1]["done"]=(status.lower()=="done")
    await interaction.response.send_message(f"✅ Updated item {index} to **{status}**.", ephemeral=True)

@bot.tree.command(name="checklist_show", description="Show the checklist for this task.")
async def checklist_show(interaction: discord.Interaction):
    if not interaction.channel.name.startswith("ticket-"):
        return await interaction.response.send_message("This command can only be used in a ticket channel.", ephemeral=True)

    ticket=TICKET_DATA.get(interaction.channel.id)
    if not ticket or "checklist" not in ticket or not ticket["checklist"]:
        return await interaction.response.send_message("No checklist found for this ticket.", ephemeral=True)
    
    embed=discord.Embed(
        title=f"Checklist: {ticket.get('task_title','Untitled Task')}",
        color=discord.Color.blurple( )
    )

    embed = discord.Embed(title=f"Checklist: {ticket.get('task_title', 'Untitled Task')}", color=discord.Color.blurple())
    
    for idx,item in enumerate(ticket["checklist"], start=1):
        status_emoji = "✅" if item["done"] else "⌛"
        status_text = "done" if item["done"] else "pending"
        embed.add_field(name=f"{status_emoji} {idx}.{item['text']}", value=f"Status: {status_text}", inline=False)
        
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="dashboard", description="Open the ticket management dashboard")
async def dashboard(interaction: discord.Interaction):
  view= TicketDashboard()
  await interaction.response.send_message("Ticket Management Dashboard:", view=view, ephemeral=True)
  
if __name__ == "__main__":
    if not TOKEN:
        logger.error("DISCORD_TOKEN is not set in the .env file.")
        exit(1)
    bot.run(TOKEN)