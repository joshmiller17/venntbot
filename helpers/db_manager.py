""""
Copyright © Krypton 2019-2023 - https://github.com/kkrypt0nn (https://krypton.ninja)
Description:
🐍 A simple template to start to code your own and personalized discord bot in Python programming language.

Version: 5.5.0
"""

import os

import aiosqlite

DATABASE_PATH = f"{os.path.realpath(os.path.dirname(__file__))}/../database/database.db"


async def get_blacklisted_users() -> list:
    """
    This function will return the list of all blacklisted users.

    :param user_id: The ID of the user that should be checked.
    :return: True if the user is blacklisted, False if not.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT user_id, strftime('%s', created_at) FROM blacklist"
        ) as cursor:
            result = await cursor.fetchall()
            return result


async def is_blacklisted(user_id: int) -> bool:
    """
    This function will check if a user is blacklisted.

    :param user_id: The ID of the user that should be checked.
    :return: True if the user is blacklisted, False if not.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT * FROM blacklist WHERE user_id=?", (user_id,)
        ) as cursor:
            result = await cursor.fetchone()
            return result is not None


async def add_user_to_blacklist(user_id: int) -> int:
    """
    This function will add a user based on its ID in the blacklist.

    :param user_id: The ID of the user that should be added into the blacklist.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("INSERT INTO blacklist(user_id) VALUES (?)", (user_id,))
        await db.commit()
        rows = await db.execute("SELECT COUNT(*) FROM blacklist")
        async with rows as cursor:
            result = await cursor.fetchone()
            return result[0] if result is not None else 0


async def remove_user_from_blacklist(user_id: int) -> int:
    """
    This function will remove a user based on its ID from the blacklist.

    :param user_id: The ID of the user that should be removed from the blacklist.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM blacklist WHERE user_id=?", (user_id,))
        await db.commit()
        rows = await db.execute("SELECT COUNT(*) FROM blacklist")
        async with rows as cursor:
            result = await cursor.fetchone()
            return result[0] if result is not None else 0


async def add_warn(user_id: int, server_id: int, moderator_id: int, reason: str) -> int:
    """
    This function will add a warn to the database.

    :param user_id: The ID of the user that should be warned.
    :param reason: The reason why the user should be warned.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        rows = await db.execute(
            "SELECT id FROM warns WHERE user_id=? AND server_id=? ORDER BY id DESC LIMIT 1",
            (
                user_id,
                server_id,
            ),
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            warn_id = result[0] + 1 if result is not None else 1
            await db.execute(
                "INSERT INTO warns(id, user_id, server_id, moderator_id, reason) VALUES (?, ?, ?, ?, ?)",
                (
                    warn_id,
                    user_id,
                    server_id,
                    moderator_id,
                    reason,
                ),
            )
            await db.commit()
            return warn_id
            
async def add_ability(message_id: int, ability_name: str) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute("SELECT * FROM messages WHERE ability_name = ?", (ability_name,))
        existing = await cur.fetchone()
        if existing:
            await db.execute("UPDATE messages SET message_id = ? WHERE ability_name = ?", (message_id, ability_name))
        else:
            await db.execute("INSERT INTO messages (message_id, ability_name) VALUES (?, ?)", (message_id, ability_name))
        await db.commit()
    

async def votable_name(message_id: int) -> str:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("SELECT ability_name FROM messages WHERE message_id = ?", (message_id,))
        row = await cursor.fetchone()
        return row[0]

async def get_votes() -> dict:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("SELECT ability_name, SUM(CASE WHEN value = 1 THEN 1 ELSE 0 END) AS cool, SUM(CASE WHEN value = -1 THEN 1 ELSE 0 END) AS cut FROM votes GROUP BY ability_name;")
        result = await cursor.fetchall()
        vote_dict = {}
        for row in result:
            ability_name, cool, cut = row
            vote_dict[ability_name] = {'cool': int(cool), 'cut': int(cut)}
        return vote_dict
        
    
async def get_leaderboard() -> dict:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("SELECT user_id, SUM(CASE WHEN value = 1 THEN 1 ELSE 0 END) AS cool, SUM(CASE WHEN value = -1 THEN 1 ELSE 0 END) AS cut FROM votes GROUP BY user_id;")
        result = await cursor.fetchall()
        vote_dict = {}
        for row in result:
            user_id, cool, cut = row
            vote_dict[user_id] = {'cool': int(cool), 'cut': int(cut)}
        return vote_dict

async def set_vote(user_id: str, ability_name: str, value: int) -> int:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute("SELECT value FROM votes WHERE user_id = ? AND ability_name = ?", (user_id, ability_name))
        existing_row = cur.fetchone()
        if existing_row:
            # Update the existing row
            await db.execute("UPDATE votes SET value = ? WHERE user_id = ? AND ability_name = ?", (value, user_id, ability_name))
            await db.commit()
            return existing_row[0]
        else:
            # Insert a new row
            await db.execute("INSERT INTO votes (user_id, ability_name, value) VALUES (?, ?, ?)", (user_id, ability_name, value))
        # Commit the changes
        await db.commit()
        return 0

async def remove_warn(warn_id: int, user_id: int, server_id: int) -> int:
    """
    This function will remove a warn from the database.

    :param warn_id: The ID of the warn.
    :param user_id: The ID of the user that was warned.
    :param server_id: The ID of the server where the user has been warned
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "DELETE FROM warns WHERE id=? AND user_id=? AND server_id=?",
            (
                warn_id,
                user_id,
                server_id,
            ),
        )
        await db.commit()
        rows = await db.execute(
            "SELECT COUNT(*) FROM warns WHERE user_id=? AND server_id=?",
            (
                user_id,
                server_id,
            ),
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            return result[0] if result is not None else 0


async def get_warnings(user_id: int, server_id: int) -> list:
    """
    This function will get all the warnings of a user.

    :param user_id: The ID of the user that should be checked.
    :param server_id: The ID of the server that should be checked.
    :return: A list of all the warnings of the user.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        rows = await db.execute(
            "SELECT user_id, server_id, moderator_id, reason, strftime('%s', created_at), id FROM warns WHERE user_id=? AND server_id=?",
            (
                user_id,
                server_id,
            ),
        )
        async with rows as cursor:
            result = await cursor.fetchall()
            result_list = []
            for row in result:
                result_list.append(row)
            return result_list
