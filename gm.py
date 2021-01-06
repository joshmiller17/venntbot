# --- Josh Aaron Miller 2021
# --- GM commands

import discord
from discord.ext import commands

import random, d20, operator, time, re

import importlib
db = importlib.import_module("db")
stats = importlib.import_module("stats")
init = importlib.import_module("initiative")
abilityClass = importlib.import_module("ability")
act = importlib.import_module("action")
combat = importlib.import_module("combat")
communication = importlib.import_module("communication")


class GM(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.initCog = self.bot.get_cog('Initiative')
		
	@commands.command(pass_context=True)
	async def gm_attack(self, ctx, who, target, weapon, acc_mod="+0", dmg_mod="+0", help="Roll someone's attack with a weapon. For GM use only."):
		target_entity = db.find(target)
		if target_entity is None:
			await ctx.send("No target named " + target + ", try:")
			await init.list_enemies_internal(ctx)
			return
		
		print("combat.gm_attack: " + str(who) + " " + str(target) + " " + str(weapon))
		found = False
		for w in db.weapons:
			if w["name"] == weapon:
				w_attr = w["attr"]
				w_dmg = w["dmg"]
				found = True
				weapon_dict = w
				break
				
		if not found:
			await ctx.send("Unrecognized weapon: " + str(weapon) + ".")
			return
			
		atkr = db.find(who)
		val = atkr.get_stat(w_attr)
		acc = val * 10 + stats.clean_modifier(acc_mod)
		acc_mods = atkr.mods.get_modifier_by_stat("ACC")
		if acc_mods is not None:
			await ctx.send("Accuracy modifiers: " + str(acc_mods.total()) + " from " + " and ".join(acc_mods.sources))
			acc += acc_mods.total()
		if "mods" in weapon_dict and "ACC" in weapon_dict["mods"]:
			acc += stats.clean_modifier(weapon_dict["mods"]["ACC"])
			await ctx.send(weapon_dict["mods"]["ACC"] + " ACC from " + str(weapon))
		vim = target_entity.get_stat("VIM")
		
		db.LAST_ACTION = act.Action(act.ActionType.ATTACK, weapon)
		db.LAST_ACTION.add_effect(act.ActionRole.USER, atkr, {"A":2})
		atkr.actions -= 2
		
		await ctx.send(who + " attacks " + target + " with a " + weapon + "!")
		rollstr = "(" + w_dmg + "[" + weapon + "] +" + str(val) + "[" + w_attr + "])" + (dmg_mod if dmg_mod != "+0" else "")
		mods = atkr.mods.get_modifier_by_stat("DMG")
		if mods is not None:
			for i in range(len(mods.sources)):
				rollstr += "+{0} [{1}]".format(mods.vals[i], mods.sources[i])
		
		print("combat.gm_attack: rolling " + rollstr)
		total = await stats.do_roll(ctx, rollstr)
		total = await combat.check_hit(ctx, acc, vim, total)
		await combat.apply_attack(ctx, target, total)
		
		if "mods" in weapon_dict:
			for key, val in weapon_dict["mods"].items():
				if key == "BURNING":
					res = await stats.do_roll(ctx, val)
					target_entity.mods.add_modifier("BURNING", "burning", res)
					await ctx.send(target + " takes " + str(res) + " burning!")
				if key == "BLEEDING":
					res = await stats.do_roll(ctx, val)
					target_entity.mods.add_modifier("BLEEDING", "bleeding", res)
					await ctx.send(target + " takes " + str(res) + " bleeding!")
		
		await communication.suggest_quick_actions(db.QUICK_CTX, self.initCog.whose_turn) 
		
		
		
	@commands.command(pass_context=True)
	async def gm_set_primary_weapon(self, ctx, who, weapon, help="Set someone's primary weapon type. For GM use only."):
		entity = db.get_player_file(who)
		entity["primary_weapon"] = weapon
		db.save_characters()
		await ctx.message.add_reaction(db.OK)
		
		
	@commands.command(pass_context=True)
	async def gm_use(self, ctx, who, *ability, help="Use someone's ability. For GM use only."): 	# TODO allow the use of items
		print("combat.gm_use:")
		abiObj = abilityClass.get_ability(" ".join(ability[:]))
		user = db.find(who)
		if not user.can_afford(abiObj.cost):
			await ctx.send(who + " can't afford " + abiObj.name) # TODO add more details of why
			return
		success = await user.use_resources_verbose(ctx, abiObj.cost)
		
		db.LAST_ACTION = act.Action(act.ActionType.ABILITY, abiObj.name)
		db.LAST_ACTION.add_effect(act.ActionRole.USER, user, abiObj.cost)
		await ctx.send(who + " spent " + str(abiObj.cost)) # TEST clean up
		
		await ctx.message.add_reaction(db.OK if success else db.NOT_OK) # TODO add more details of why
		# TODO more feedback
		await communication.suggest_quick_actions(db.QUICK_CTX, self.initCog.whose_turn) 
		
		
		
	@commands.command(pass_context=True)
	async def gm_cast(self, ctx, who, strength="normal", *spell, help="Cast someone's spell. For GM use only."):
		spell = " ".join(spell[:])
		abiObj = abilityClass.get_ability(spell)
		user = db.find(who)
		if not isinstance(strength, int):
			strength = strength.lower()
			cast_strength = 1
			if strength[0] == "h":
				cast_strength = 0
			if strength[0] == "d":
				cast_strength = 2
		else:
			cast_strength = strength
		abiObj.cost["M"] = abiObj.mp_costs[cast_strength]
		if not user.can_afford(abiObj.cost):
			await ctx.send(who + " can't afford " + abiObj.name) # TODO add more details of why
			return
		success = await user.use_resources_verbose(ctx, abiObj.cost)
		
		db.LAST_ACTION = act.Action(act.ActionType.SPELL, abiObj.name)
		db.LAST_ACTION.add_effect(act.ActionRole.USER, user, abiObj.cost)
		await ctx.send(who + " spent " + str(abiObj.cost)) # TEST clean up
		
		await ctx.message.add_reaction(db.OK if success else db.NOT_OK) # TODO add more details of why
		# TODO more feedback
		roll_res = stats.do_check(user, "SPI")
		dl = int(abiObj.casting_dl[cast_strength])
		if roll_res >= dl:
			await ctx.send("Success! ({0} > {1})".format(roll_res, dl))
		else:
			await ctx.send("Failure! ({0} < {1})".format(roll_res, dl))
		await communication.suggest_quick_actions(db.QUICK_CTX, self.initCog.whose_turn) 