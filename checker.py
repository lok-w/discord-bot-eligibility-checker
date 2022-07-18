from unittest import result
import nextcord
from nextcord.ext import commands
from oauth2client.service_account import ServiceAccountCredentials
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import logging
import gspread_asyncio
import string


logger = logging.getLogger('nextcord')
logger.setLevel(logging.ERROR)
handler = logging.FileHandler(filename='nextcord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

global bot_msg


TESTING_GUILD_ID = 00000000000000000
my_token = "my_token"
channel_id = 00000000000000000
og_id = 00000000000000000
whitelist_id = 00000000000000000
bot_msg = None
spreadsheet_id = "spreadsheet_id"
list_sheet_id = 0
input_sheet_id = 00000000000000000


def get_creds():
    creds = Credentials.from_service_account_file("discord-bot-350507-57cf2e5864b5.json")
    scoped = creds.with_scopes([
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ])
    return scoped

agcm = gspread_asyncio.AsyncioGspreadClientManager(get_creds, gspread_delay=0.3)


# # 0 = A; 1 = B; 2 = C etc.
def n2a(n,b=string.ascii_uppercase):
   d, m = divmod(n,len(b))
   return n2a(d-1,b)+b[m] if d else b[m]


async def submit_async(agcm, full_username, wallet, role_str, amount):
    agc = await agcm.authorize()

    ss = await agc.open_by_key(spreadsheet_id)

    list_worksheet = await ss.get_worksheet_by_id(list_sheet_id)
    input_worksheet = await ss.get_worksheet_by_id(input_sheet_id)

    input_cell = await input_worksheet.find(query=full_username, in_column=3)

    if input_cell != None:
        response = f"Success! Your record has been changed to {wallet}."

        date_time = datetime.now()
        date_time = date_time.strftime("%m/%d/%Y %H:%M:%S")

        await input_worksheet.batch_update([{
                'range': f"A{input_cell.row}:B{input_cell.row}",
                'values': [[f"{wallet}", f"{role_str}"]],
            }, {
                'range': f"D{input_cell.row}",
                'values': [[f"{date_time}"]],
            }])
        
        list_cell = await list_worksheet.find(query=full_username, in_column=4)

        await list_worksheet.batch_update([{
                    'range': f"A{list_cell.row}:C{list_cell.row}",
                    'values': [[f"{wallet}", f"{role_str}", amount]],
                }])
        
        return response
    else:
        response = f"Success! Your input has been submitted as {wallet}."

        list_total = len(await list_worksheet.col_values(1))
        input_total = len(await input_worksheet.col_values(1))

        list_total += 1
        input_total += 1

        date_time = datetime.now()
        date_time = date_time.strftime("%m/%d/%Y %H:%M:%S")

        await input_worksheet.batch_update([{
                    'range': f"A{input_total}:D{input_total}",
                    'values': [[f"{wallet}", f"{role_str}", f"{full_username}", f"{date_time}" ]],
                }])
        await list_worksheet.batch_update([{
                    'range': f"A{list_total}:F{list_total}",
                    'values': [[f"{wallet}", f"{role_str}", amount, f"{full_username}", 0, 0 ]],
                }])
        
        return response


async def check_async(agcm, wallet):
    agc = await agcm.authorize()

    ss = await agc.open_by_key(spreadsheet_id)

    list_worksheet = await ss.get_worksheet_by_id(list_sheet_id)

    found_cell = False
    list_cell = await list_worksheet.find(query=wallet, in_column=1)
    if list_cell != None:
        found_cell = True
    else:
        wallet_lower = wallet.lower()
        list_cell = await list_worksheet.find(query=wallet_lower, in_column=1)

        if list_cell != None:
            found_cell = True
        else:
            wallet_upper = wallet.upper()
            list_cell = await list_worksheet.find(query=wallet_upper, in_column=1)
            if list_cell != None:
                found_cell = True


    if found_cell:
        date_time = datetime.now()
        date_time = date_time.strftime("%m/%d/%Y %H:%M:%S")

        result = await list_worksheet.batch_get([f"C{list_cell.row}:E{list_cell.row}"])

        eligibility, user, check_count = result[0][0]

        check_count = int(check_count)
        check_count += 1
        response = f"You are eligible to {eligibility}"

        await list_worksheet.batch_update([{
                    'range': f"E{list_cell.row}",
                    'values': [[check_count]],
                }, {
                    'range': f"{n2a(4+check_count)}{list_cell.row}",
                    'values': [[f"{date_time}"]],
                }])
        
        return response
    
    else:
        response = f"You are not on the list."

        return response


bot = commands.Bot()

@bot.event
async def on_ready():
    print("Bot is started.")


    view = Wallet()
    embed = nextcord.Embed(title="Wallet Submission", color=nextcord.Color.blurple())
    embed.description=("Click the buttons below to submit and check your wallet address.")
    # embed.add_field(name="Valid Roles: ", value=f"<@&{og_id}> <@&{whitelist_id}>", inline=False)

    channel = bot.get_channel(channel_id)

    global bot_msg
    bot_msg = await channel.send(embeds=[embed],view=view)
    await view.wait()


class Wallet_Input(nextcord.ui.Modal):
    def __init__(self):
        super().__init__(
            "Name",
            timeout=2*60,  # 2 minutes
        )
        self.role = ""
        self.wallet = nextcord.ui.TextInput(
            label="ENTER YOUR INPUT HERE.",
            min_length=42,
            max_length=42,
        )
        self.add_item(self.wallet)


    async def callback(self, interaction: nextcord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True);

        missing_role = True
        role_str = ""
        amount = 0
        for role in interaction.user.roles:
            if role.id == whitelist_id:
                role_str = "Role 1"
                amount = 2
                missing_role = False
            
            if role.id == og_id:
                role_str = "Role 2"
                amount = 3
                missing_role = False

        
        if missing_role:
            response = f"You are not on the list."
            await interaction.followup.send(content=response, ephemeral=True)
            return

        if self.wallet.value[:2] != "":
            response = f"Invalid input. Address must start with '0x'."
            await interaction.followup.send(content=response, ephemeral=True)
            return

        full_username = f"{interaction.user.name}#{interaction.user.discriminator}"
        
        response = await submit_async(agcm=agcm, full_username=full_username, wallet=self.wallet.value, role_str=role_str, amount=amount)

        await interaction.followup.send(content=response, ephemeral=True)
        return


class Wallet_Check(nextcord.ui.Modal):
    def __init__(self):
        super().__init__(
            "Name",
            timeout=2*60,  # 2 minutes
        )
        self.role = ""
        self.wallet = nextcord.ui.TextInput(
            label="ENTER YOUR INPUT HERE.",
            min_length=42,
            max_length=42,
        )
        self.add_item(self.wallet)


    async def callback(self, interaction: nextcord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        if self.wallet.value[:2] != "0x":
            response = f"Invalid input. Address must start with '0x'."
            await interaction.followup.send(content=response, ephemeral=True)
            return

        response = await check_async(agcm=agcm, wallet=self.wallet.value)

        await interaction.followup.send(content=response, ephemeral=True)
        return


class Wallet(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.value = None
    
    @nextcord.ui.button(label="Submit", style=nextcord.ButtonStyle.primary)
    async def submit(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        modal = Wallet_Input()
        await interaction.response.send_modal(modal)
    
    @nextcord.ui.button(label="Check", style=nextcord.ButtonStyle.success)
    async def check(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        modal = Wallet_Check()
        await interaction.response.send_modal(modal)


@bot.slash_command(guild_ids=[TESTING_GUILD_ID])
async def restart(interaction: nextcord.Interaction):
    await interaction.response.send_message(content="Restarting ...", ephemeral=True)

    view = Wallet()
    embed = nextcord.Embed(title="Wallet Submission", color=nextcord.Color.blurple())
    embed.description=("Click the buttons below to submit and check your wallet address.")
    # embed.add_field(name="Valid Roles: ", value=f"<@&{og_id}> <@&{whitelist_id}>", inline=False)

    channel = bot.get_channel(channel_id)

    global bot_msg
    await bot_msg.delete()
    bot_msg = await channel.send(embeds=[embed],view=view)
    await view.wait()
    

@bot.slash_command(guild_ids=[TESTING_GUILD_ID])
async def close(interaction: nextcord.Interaction):
    await interaction.response.send_message(content="Closing ...", ephemeral=True)

    global bot_msg
    await bot_msg.delete()


@bot.slash_command(guild_ids=[TESTING_GUILD_ID])
async def start(interaction: nextcord.Interaction):
    await interaction.response.send_message(content="Starting ...", ephemeral=True)

    view = Wallet()
    embed = nextcord.Embed(title="Wallet Submission", color=nextcord.Color.blurple())
    embed.description=("Click the buttons below to submit and check your wallet address.")
    # embed.add_field(name="Valid Roles: ", value=f"<@&{og_id}> <@&{whitelist_id}>", inline=False)

    channel = bot.get_channel(channel_id)

    global bot_msg
    bot_msg = await channel.send(embeds=[embed],view=view)
    await view.wait()

    
bot.run(my_token)