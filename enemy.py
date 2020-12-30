class Enemy:
	def __init__(self, name, hp, vim, acc, armor, dmg):
		self.name = name
		self.hp = hp
		self.max_hp = hp
		self.vim = vim
		self.acc = acc
		self.armor = armor
		self.dmg = dmg