# --- Josh Aaron Miller 2020
# --- Google Sheets commands

import discord
from discord.ext import commands



def get_sheet_id(char_name):
	for character in characters:
		if character["name"] == char_name:
			return character["ID"]
	print("ERROR: no sheet found for " + char_name)
	return ""

def get_from_sheets(spreadsheet_id, sheet_range):
	result = sheet.values().get(spreadsheetId=spreadsheet_id,
								range=sheet_range).execute()
	values = result.get('values', [])
	return values
	
def update_to_sheets(spreadsheet_id, sheet_range, vs):
	body = {'values' : vs}
	result = service.spreadsheets().values().update(
	spreadsheetId=spreadsheet_id, range=sheet_range,
	valueInputOption='RAW', body=body).execute()



	

class Sheets(commands.Cog):
	def __init__(self, bot):
		self.bot = bot




	