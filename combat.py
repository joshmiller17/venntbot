# --- Josh Aaron Miller 2020
# --- Combat commands

import discord
from discord.ext import commands




turn_order = {} # who : value + 0.1 * score + 0.01* rand float for tie breaking
init_index = 99

combatants = [] # set of all active Players and Enemies


	
def compare_hp(current, max):
	percent = (1.0 * current) / (1.0 * max)
	if percent > 0.9:
		return "healthy."
	if percent >  0.7:
		return "scratched."
	if percent > 0.5:
		return "hurt."
	if percent > 0.3:
		return "bloodied!"
	if percent > 0.1:
		return "severely wounded!"
	if percent > 0:
		return "near death!"
	return "dead!"
	

def make_enemies(number, name):
	ret = []
	for enemy in enemies:
		if enemy["name"] == name:
			if number == 1:
				return [Enemy(enemy["name"], enemy["hp"], enemy["vim"], enemy["acc"], enemy["armor"], enemy["dmg"])]
			else:
				for i in range(1, number+1): #1-index
					ret.append(Enemy(enemy["name"] + str(i), enemy["hp"], enemy["vim"],  enemy["acc"], enemy["armor"], enemy["dmg"]))
				return ret
				
def get_enemy(e):
	for c in combatants:
		if isinstance(c, Enemy):
			if c.name == e:
				return c
				
async def apply_attack(ctx, target, dmg):
	if is_player(target):
		armor = get_attr_val(target, "armor")
		true_dmg = max(dmg - armor, 0)
		new_val = get_attr_val(target, "HP") - true_dmg
		await gm_set(ctx, target, new_val, "HP")
		await ctx.send(target + " takes " + str(true_dmg) + " damage!")
		await examine(ctx, target)
	else:
		# assume target is the Enemy type
		true_dmg = max(dmg - target.armor, 0)
		target.hp -= true_dmg
		await ctx.send(target.name + " takes " + str(true_dmg) + " damage!")
		await examine(ctx, target.name)

class Combat(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

@client.command(pass_context=True)
async def next_turn(ctx, help = "Advance the turn order"):
	global turn_order, init_index
	sorted_turns = sorted(turn_order.items(), key=operator.itemgetter(1),reverse=True)
	print(sorted_turns)
	for who, val in sorted_turns:
		if val < init_index:
			init_index = val
			await ctx.send("Now " + who + "'s turn.")
			return
	# reached the bottom, wrap around
	init_index = 99
	await ctx.send("New round!")
	await next_turn(ctx)
	
	
		
@client.command(pass_context=True)
async def add_combatant(ctx, who, help="Add player (or 'all') to active combat."):
	if who == 'all':
		for player in players:
			combatants.append(player)
	else:
		combatants.append(who)
	await ctx.message.add_reaction(OK)
	
@client.command(pass_context=True)
async def add_enemies(ctx, num, name, help="Add X enemies to active combat. Usage: $add_enemies number name"):
	num = int(num)
	new_enemies = make_enemies(num, name)
	for e in new_enemies:
		combatants.append(e)
	await ctx.message.add_reaction(OK)
	

@client.command(pass_context=True)
async def clear_combatants(ctx, who, help="End combat."):
	combatants = []
	await ctx.message.add_reaction(OK)
	
	
	@client.command(pass_context=True)
async def turn_order(ctx, help = "Get the turn order."):
	ret = "Turn order: "
	turns = []
	sorted_turns = sorted(turn_order.items(), key=operator.itemgetter(1),reverse=True)
	for who, val in sorted_turns:
		turns.append(who)
	ret += ', '.join(turns)
	await ctx.send(ret)

@client.command(pass_context=True)
async def new_init(ctx, help = "Rolls a new initiative for everyone."):
	turn_order = {} # clear turn order
	for player in players:
		await add_turn(ctx, player, check_no_print(player, "init"))
	await ctx.message.add_reaction(OK)

@client.command(pass_context=True)
async def add_turn(ctx, who, init_val, help= "Usage: $add_turn character roll_result"):
	turn_order[who] = int(init_val) + 0.1 * get_attr_val(who, "init") + 0.01 * random.random()
	await ctx.message.add_reaction(OK)



@client.command(pass_context=True)
async def enemy_attack(ctx, attacker, target, help='Usage: $enemy_attack attacker target'):
	await ctx.send(attacker + " attacks " + target + "!")
	total = await roll(ctx, get_enemy(attacker).dmg)
	
	acc = get_enemy(attacker).acc
	vim = get_attr_val(target, "vim")
	
	if acc < vim:
		await ctx.send("*A glancing blow...*")
		total = half(total)
	else:
		await ctx.send("*A direct hit!*")
	await apply_attack(ctx, target, total)
	
@client.command(pass_context=True)
async def gm_attack(ctx, who, target, weapon, help='Roll an attack with a weapon. Usage: $attack who target weapon-type'):
	found = False
	for w in weapons:
		if w["name"] == weapon:
			w_attr = w["attr"]
			w_dmg = w["dmg"]
			found = True
			break
	
	acc = get_attr_val(who, w_attr) * 10
	vim = get_enemy(target).vim
	
	if not found:
		ctx.send("Unrecognized weapon: " + weapon + ".")
	else:
		val = get_attr_val(who, w_attr)
		await ctx.send(who + " attacks " + target + " with a " + weapon + "!")
		total = await roll(ctx, w_dmg + "+" + str(val))
		if acc < vim:
			await ctx.send("*A glancing blow...*")
			total = half(total)
		else:
			await ctx.send("*A direct hit!*")
		await apply_attack(ctx, get_enemy(target), total)
	
@client.command(pass_context=True)
async def attack(ctx, target, weapon, help='Roll an attack with a weapon. Usage: $attack target weapon-type'):
	who = get_char_name(ctx.message.author)
	found = False
	for w in weapons:
		if w["name"] == weapon:
			w_attr = w["attr"]
			w_dmg = w["dmg"]
			found = True
			break
	
	acc = get_attr_val(who, w_attr) * 10
	vim = get_enemy(target).vim
	
	if not found:
		ctx.send("Unrecognized weapon: " + weapon + ".")
	else:
		val = get_attr_val(who, w_attr)
		await ctx.send(who + " attacks " + target + " with a " + weapon + "!")
		total = await roll(ctx, w_dmg + "+" + str(val))
		if acc < vim:
			await ctx.send("*A glancing blow...*")
			total = half(total)
		else:
			await ctx.send("*A direct hit!*")
		await apply_attack(ctx, target, total)
	