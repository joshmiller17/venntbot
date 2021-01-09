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
logClass = importlib.import_module("logger")
logger = logClass.Logger("gm")

class GM(commands.Cog):
	"""Commands for the GM."""

	def __init__(self, bot):
		self.bot = bot
		self.initCog = self.bot.get_cog('Initiative')
		
	@commands.command(pass_context=True)
	async def gm_attack(self, ctx, who, target, weapon, acc_mod="+0", dmg_mod="+0"):
		"""Roll someone's attack with a weapon. For GM use only."""
		target_ent = db.find(target)
		if target_ent is None:
			await communication.send(ctx,"No target named " + target + ", try:")
			await init.list_enemies_internal(ctx)
			return
		
		logger.log("gm_attack", str(who) + " " + str(target) + " " + str(weapon))
		found = False
		for w in db.weapons:
			if w["name"] == weapon:
				w_attr = w["attr"]
				w_dmg = w["dmg"]
				found = True
				weapon_dict = w
				break
				
		if not found:
			await communication.send(ctx,"Unrecognized weapon: " + str(weapon) + ".")
			return
			
		attacker_ent = db.find(who)
		relevant_attr = attacker_ent.get_stat(w_attr)
		acc = relevant_attr * 10 + stats.clean_modifier(acc_mod)
		acc_mods = attacker_ent.mods.get_modifier_by_stat("ACC")
		if acc_mods is not None:
			await communication.send(ctx,"Accuracy modifiers: " + str(acc_mods.total()) + " from " + " and ".join(acc_mods.sources))
			acc += acc_mods.total()
		if "mods" in weapon_dict and "ACC" in weapon_dict["mods"]:
			acc += stats.clean_modifier(weapon_dict["mods"]["ACC"])
			await communication.send(ctx,weapon_dict["mods"]["ACC"] + " ACC from " + weapon)
		vim = target_ent.get_stat("VIM")
		
		db.LAST_ACTION = act.Action(act.ActionType.ATTACK, weapon)
		db.LAST_ACTION.add_effect(act.ActionRole.USER, attacker_ent, {"A":2})
		attacker_ent.actions -= 2
		
		await communication.send(ctx,who + " attacks " + target + " with a " + weapon + "!")
		rollstr = "(" + w_dmg + "[" + weapon + "] +" + str(relevant_attr) + "[" + w_attr + "])" + (dmg_mod if dmg_mod != "+0" else "")
		mods = attacker_ent.mods.get_modifier_by_stat("DMG")
		if mods is not None:
			for i in range(len(mods.sources)):
				rollstr += "+{0} [{1}]".format(mods.vals[i], mods.sources[i])
		
		logger.log("gm_attack", "rolling " + rollstr)
		total = await stats.do_roll(ctx, rollstr)
		total = await combat.check_hit(ctx, acc, vim, total)
		await combat.apply_attack(ctx, target_ent, total)
		
		if "mods" in weapon_dict:
			for key, val in weapon_dict["mods"].items():
				if key == "BURNING":
					res = await stats.do_roll(ctx, val)
					target_ent.mods.add_modifier("BURNING", "burning", res)
					await communication.send(ctx,target + " takes " + str(res) + " burning!")
				if key == "BLEEDING":
					res = await stats.do_roll(ctx, val)
					target_ent.mods.add_modifier("BLEEDING", "bleeding", res)
					await communication.send(ctx,target + " takes " + str(res) + " bleeding!")
	

	@commands.command(pass_context=True)
	async def gm_set_primary_weapon(self, ctx, who, weapon):
		"""Set someone's primary weapon type. For GM use only."""
		entity = db.find(who)
		entity["primary_weapon"] = weapon
		db.save_characters()
		await ctx.message.add_reaction(db.OK)
		
	async def why_cant_afford(self, ctx, entity, abiObj):
		if abiObj.cost is None:
			await communication.send(ctx,abiObj.name + " has no defined cost.")
			return
		await communication.send(ctx,entity.display_name() + " can't afford " + abiObj.name)
		reasons = []
		for key, val in abiObj.cost.items():
			if key == 'A' and entity.actions < val:
				reasons.append("{0} has {1} action(s) but needs {2}".format(entity.display_name(), entity.actions, val))
			if key == 'R' and entity.reactions < val:
				reasons.append("{0} has {1} reaction(s) but needs {2}".format(entity.display_name(), entity.reactions, val))
			if key == 'M' and entity.actions < val:
				reasons.append("{0} has {1} MP but needs {2}".format(entity.display_name(), entity.attrs["MP"], val))
			if key == 'V' and entity.actions < val:
				reasons.append("{0} has {1} Vim but needs {2}".format(entity.display_name(), entity.attrs["VIM"], val))
		await communication.send(ctx,"```\n{0}\n```".format("\n".join(reasons)))
			
	async def describe_spend(self, ctx, entity, abiObj):
		spent = []
		for key, val in abiObj.cost.items():
			if key == 'A' and entity.actions < val:
				spent.append("{0} spent {1} action(s)".format(entity.display_name(), val))
			if key == 'R' and entity.reactions < val:
				spent.append("{0} spent {1} reaction(s)".format(entity.display_name(), val))
			if key == 'M' and entity.actions < val:
				spent.append("{0} spent {1} MP".format(entity.display_name(), val))
			if key == 'V' and entity.actions < val:
				spent.append("{0} spent {1} Vim".format(entity.display_name(), val))
		if spent != []:
			await communication.send(ctx,"\n".join(spent))
			
	@commands.command(pass_context=True)
	async def gm_skills(self, ctx, who):
		"""List someone's skills."""
		entity = db.find(who)
		await communication.send(ctx,", ".join(entity.skills))
		
	@commands.command(pass_context=True)
	async def gm_rest(self, ctx, who, bonus="+0", hours="9"):
		entity = db.find(who)
		hours_clean = clean_modifier(hours)
		bonus_clean = clean_modifier(bonus)
		strength = entity.get_stat("STR") + bonus_clean
		strength = max(strength, 1) # min 1
		entity.change_resource_verbose(ctx, "MP", hours_clean)
		entity.change_resource_verbose(ctx, "VIM", hours_clean)
		entity.change_resource_verbose(ctx, "HP", strength)
		
	@commands.command(pass_context=True)
	async def gm_use(self, ctx, who, *ability):
		"""Use someone's ability. For GM use only."""
		if not abilityClass.ability_exists(*ability):
			await communication.send(ctx,"I'm not sure what ability that is.")
			return
		abiObj = abilityClass.get_ability(" ".join(ability[:]))
		user = db.find(who)
		if not user.can_afford(abiObj.cost):
			await self.why_cant_afford(ctx, user, abiObj)
			return
		success = await user.use_resources_verbose(ctx, abiObj.cost)
		
		db.LAST_ACTION = act.Action(act.ActionType.ABILITY, abiObj.name)
		db.LAST_ACTION.add_effect(act.ActionRole.USER, user, abiObj.cost)
		await self.describe_spend(ctx, user, abiObj)
		
		await ctx.message.add_reaction(db.OK if success else db.NOT_OK)
		# TODO more feedback
		
	@commands.command(pass_context=True)
	async def gm_cast(self, ctx, who, strength="normal", *spell):
		"""Cast someone's spell. For GM use only."""
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
			await self.why_cant_afford(ctx, user, abiObj)
			return
		success = await user.use_resources_verbose(ctx, abiObj.cost)
		
		db.LAST_ACTION = act.Action(act.ActionType.SPELL, abiObj.name)
		db.LAST_ACTION.add_effect(act.ActionRole.USER, user, abiObj.cost)
		await self.describe_spend(ctx, user, abiObj)
		
		await ctx.message.add_reaction(db.OK if success else db.NOT_OK)
		# TODO more feedback
		
		roll_res = stats.do_check(user, "SPI")
		dl = int(abiObj.casting_dl[cast_strength])
		if roll_res >= dl:
			await communication.send(ctx,"Success! ({0} > {1})".format(roll_res, dl))
		else:
			await communication.send(ctx,"Failure! ({0} < {1})".format(roll_res, dl))