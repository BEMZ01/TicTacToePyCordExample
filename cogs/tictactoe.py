# cog to implement a tictactoe game
import random

import discord
from discord.ext import commands
from discord import Member
import asyncio
import sqlite3


def setup(bot):
    bot.add_cog(TicTacToe(bot))


def check(reaction, user):
    message = reaction.message
    return user != message.author and str(reaction.emoji) == "✅"


def magic_square_test(magic_square):
    iSize = len(magic_square[0])
    sum_list = []
    # Horizontal Part:
    sum_list.extend([sum(lines) for lines in magic_square])

    # Vertical Part:
    for col in range(iSize):
        sum_list.append(sum(row[col] for row in magic_square))

    # Diagonals Part
    result1 = 0
    for i in range(0, iSize):
        result1 += magic_square[i][i]
    sum_list.append(result1)

    result2 = 0
    for i in range(iSize - 1, -1, -1):
        result2 += magic_square[i][i]
    sum_list.append(result2)

    if len(set(sum_list)) > 1:
        return False
    return True


class TicTacToe(commands.Cog, name="TicTacToe Game"):
    def __init__(self, bot):
        self.game_message_id = None
        self.player1 = None
        self.player2 = None
        self.turn = None
        self.bot = bot
        self.board = ["0", "0", "0", "0", "0", "0", "0", "0", "0"]
        self.winning_positions = [
            [0, 1, 2],
            [3, 4, 5],
            [6, 7, 8],
            [0, 3, 6],
            [1, 4, 7],
            [2, 5, 8],
            [0, 4, 8],
            [2, 4, 6],
        ]

    @discord.slash_command(name="play", description="Play a game vs a friend!")
    async def play(self, ctx, player2: Member):
        # check if a game is already in progress
        if self.game_message_id is not None:
            await ctx.respond("A game is already in progress!", ephemeral=True)
            return
        else:
            # use emojis to get player2 consent to play
            self.player1 = ctx.author
            self.player2 = player2
            await ctx.respond("Waiting for player2 to accept...", delete_after=30, ephemeral=True)
            message = await ctx.channel.send(f"{player2.mention} do you accept this challenge?", delete_after=30)
            await message.add_reaction("✅")
            await message.add_reaction("❌")
            try:
                reaction, user = await self.bot.wait_for("reaction_add", check=self.check_p2_check, timeout=30)
            except asyncio.TimeoutError:  # That way the bot doesn't wait forever for a reaction
                await message.channel.send("Game stopped due to inactivity.", delete_after=10)
                return
            if reaction:
                # delete previous message
                await message.delete()
                if str(reaction) == "✅":
                    self.turn = random.choice([1, 2])
                    self.game_message_id = await ctx.send(f"Starting game between {self.player1.name} and {self.player2.name}!")
                    await self.add_emoijs()
                    await self.update_board()
                    while True:
                        if self.turn == 1:
                            try:
                                reaction, user = await self.bot.wait_for("reaction_add", check=self.check_p1_turn, timeout=30)
                            except asyncio.TimeoutError:
                                await ctx.send("Game stopped due to inactivity.", delete_after=10)
                                await self.game_message_id.delete()
                                self.game_message_id = None
                                self.board = ["0", "0", "0", "0", "0", "0", "0", "0", "0"]
                                return
                            if reaction and self.check_colision(reaction):
                                self.board[int(str(reaction)[0]) - 1] = "1"
                                self.turn = 2
                                await self.update_board()
                                if self.check_win() == 1:
                                    await self.game_message_id.edit(f"🎉* {self.player1.name} (Player 1) won!*🎉",
                                                                    delete_after=15)
                                    await self.game_message_id.clear_reactions()
                                    self.game_message_id = None
                                    self.board = ["0", "0", "0", "0", "0", "0", "0", "0", "0"]
                                    return
                                elif self.check_win() == -1:
                                    await self.game_message_id.edit(f"🎉* Nice Draw!*🎉",
                                                                    delete_after=15)
                                    await self.game_message_id.clear_reactions()
                                    self.game_message_id = None
                                    self.board = ["0", "0", "0", "0", "0", "0", "0", "0", "0"]
                                    return
                            await self.game_message_id.remove_reaction(reaction, user)
                            await self.game_message_id.add_reaction(reaction)
                        elif self.turn == 2:
                            try:
                                reaction, user = await self.bot.wait_for("reaction_add", check=self.check_p2_turn, timeout=30)
                            except asyncio.TimeoutError:
                                await ctx.send("Game stopped due to inactivity.", delete_after=10)
                                await self.game_message_id.delete()
                                self.game_message_id = None
                                self.board = ["0", "0", "0", "0", "0", "0", "0", "0", "0"]
                                return
                            if reaction and self.check_colision(reaction):
                                self.board[int(str(reaction)[0]) - 1] = "2"
                                self.turn = 1
                                await self.update_board()
                                if self.check_win() == 2:
                                    await self.game_message_id.edit(f"🎉* {self.player2.name} (Player 2) won!*🎉",
                                                                    delete_after=15)
                                    await self.game_message_id.clear_reactions()
                                    self.game_message_id = None
                                    self.board = ["0", "0", "0", "0", "0", "0", "0", "0", "0"]
                                    return
                                elif self.check_win() == -1:
                                    await self.game_message_id.edit(f"🎉* Nice Draw!*🎉",
                                                                    delete_after=15)
                                    await self.game_message_id.clear_reactions()
                                    self.game_message_id = None
                                    self.board = ["0", "0", "0", "0", "0", "0", "0", "0", "0"]
                                    return
                            await self.game_message_id.remove_reaction(reaction, user)
                            await self.game_message_id.add_reaction(reaction)

                elif str(reaction) == "❌":
                    await ctx.send("Game stopped.", delete_after=10)
                    await message.delete()
                    self.game_message_id = None
                    self.board = ["0", "0", "0", "0", "0", "0", "0", "0", "0"]
                    return

    @discord.slash_command(name="aiplay", description="Play a game vs a computer!")
    async def play_ai(self, ctx):
        await ctx.respond("Initializing computer...", delete_after=5, ephemeral=True)
        # check if a game is already in progress
        if self.game_message_id is not None:
            await ctx.respond("A game is already in progress!", ephemeral=True)
            return
        else:
            # use emojis to get player2 consent to play
            self.player1 = ctx.author
            self.player2 = "Computer"
            self.turn = random.choice([1, 2])
            self.game_message_id = await ctx.send(f"Starting game between {self.player1.name} and {self.player2}!")
            await self.add_emoijs()
            await self.update_board()
            while True:
                if self.turn == 1:
                    try:
                        reaction, user = await self.bot.wait_for("reaction_add", check=self.check_p1_turn, timeout=30)
                    except asyncio.TimeoutError:
                        await ctx.send("Game stopped due to inactivity.", delete_after=10)
                        await self.game_message_id.delete()
                        self.game_message_id = None
                        self.board = ["0", "0", "0", "0", "0", "0", "0", "0", "0"]
                        return
                    if reaction and self.check_colision(reaction):
                        self.board[int(str(reaction)[0]) - 1] = "1"
                        self.turn = 2
                        await self.update_board()
                        if self.check_win() == 1:
                            await self.game_message_id.edit(f"🎉* {self.player1.name} (Player 1) won!*🎉",
                                                            delete_after=15)
                            await self.game_message_id.clear_reactions()
                            self.game_message_id = None
                            self.board = ["0", "0", "0", "0", "0", "0", "0", "0", "0"]
                            return
                        elif self.check_win() == -1:
                            await self.game_message_id.edit(f"🎉* Nice Draw!*🎉",
                                                            delete_after=15)
                            await self.game_message_id.clear_reactions()
                            self.game_message_id = None
                            self.board = ["0", "0", "0", "0", "0", "0", "0", "0", "0"]
                            return
                    await self.game_message_id.remove_reaction(reaction, user)
                    await self.game_message_id.add_reaction(reaction)
                elif self.turn == 2:
                    await asyncio.sleep(1)
                    await self.ai_turn()
                    self.turn = 1
                    await self.update_board()
                    if self.check_win() == 2:
                        await self.game_message_id.edit(f"🎉* {self.player2} (Player 2) won!*🎉",
                                                        delete_after=15)
                        await self.game_message_id.clear_reactions()
                        self.game_message_id = None
                        self.board = ["0", "0", "0", "0", "0", "0", "0", "0", "0"]
                        return
                    elif self.check_win() == -1:
                        await self.game_message_id.edit(f"🎉* Nice Draw!*🎉",
                                                        delete_after=15)
                        await self.game_message_id.clear_reactions()
                        self.game_message_id = None
                        self.board = ["0", "0", "0", "0", "0", "0", "0", "0", "0"]
                        return

    async def ai_turn(self):
        bias = random.choice([0, 1])
        if bias == 0: # prefer to win
            if not self.check_near_win(2, 2) is None:
                index = self.check_near_win(2, 2)
                if self.check_ai_colision(index):
                    print("winning at position " + str(self.check_near_win(2, 2)))
                    self.board[index] = "2"
                    return
                else:
                    self.board[random.choice(self.get_empty_positions())] = "2"
                    return
            elif not self.check_near_win(2, 1) is None:
                index = self.check_near_win(2, 1)
                if self.check_ai_colision(index):
                    print("blocking at position " + str(index))
                    self.board[index] = "2"
                    return
                else:
                    self.board[random.choice(self.get_empty_positions())] = "2"
                    return
        if bias == 1: # prefer to block
            if not self.check_near_win(2, 1) is None:
                index = self.check_near_win(2, 1)
                if self.check_ai_colision(index):
                    print("blocking at position " + str(index))
                    self.board[index] = "2"
                    return
                else:
                    print("random")
                    self.board[random.choice(self.get_empty_positions())] = "2"
                    return
            elif not self.check_near_win(2, 2) is None:
                index = self.check_near_win(2, 2)
                if self.check_ai_colision(index):
                    print("winning at position " + str(self.check_near_win(2, 2)))
                    self.board[index] = "2"
                    return
                else:
                    print("random")
                    self.board[random.choice(self.get_empty_positions())] = "2"
                    return
        # if no near win, play a random move
        while True:
            move = random.randint(0, 8)
            if self.board[move] == "0":
                self.board[move] = "2"
                break

    def get_empty_positions(self):
        empty_positions = []
        for i in range(9):
            if self.board[i] == "0":
                empty_positions.append(i)
        return empty_positions

    async def update_board(self):
        embed = discord.Embed(title="TicTacToe", description="Use the numbers to place your mark.")
        lboard = self.board.copy()
        for x in range(0, len(lboard)):
            lboard[x] = lboard[x].replace("0", "⬜").replace("1", "❌").replace("2", "⭕")
        embed.add_field(name="⠀", value=f"{lboard[0]}⠀{lboard[1]}⠀{lboard[2]}", inline=False)
        embed.add_field(name="⠀", value=f"{lboard[3]}⠀{lboard[4]}⠀{lboard[5]}", inline=False)
        embed.add_field(name="⠀", value=f"{lboard[6]}⠀{lboard[7]}⠀{lboard[8]}", inline=False)
        if self.turn == 1:
            embed.set_footer(text=f"{self.player1.name} (Player 1)'s turn.")
        elif self.turn == 2:
            try:
                embed.set_footer(text=f"{self.player2.name} (Player 2)'s turn.")
            except AttributeError:
                embed.set_footer(text=f"{self.player2} (Player 2)'s turn.")
        await self.game_message_id.edit(embed=embed)

    async def add_emoijs(self):
        for x in ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]:
            await self.game_message_id.add_reaction(x)

    def check_p1_turn(self, reaction, user):
        return str(user) == str(self.player1) and str(reaction) in ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]

    def check_p2_turn(self, reaction, user):
        return str(user) == str(self.player2) and str(reaction) in ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]

    def check_p2_check(self, reaction, user):
        return str(user) == str(self.player2) and str(reaction.emoji) == str(reaction)

    def check_win(self):
        if self.check_draw():
            return -1
        for x in range(0, 2):
            positions = []
            for y in range(0, len(self.board)):
                if self.board[y] == str(x + 1):
                    positions.append(y)
            for z in self.winning_positions:
                if all(elem in positions for elem in z):
                    return x + 1
        return 0

    def check_draw(self):
        for x in self.board:
            if x == "0":
                return False
        return True

    def check_colision(self, reaction):
        return self.board[int(str(reaction)[0]) - 1] == "0"

    def check_ai_colision(self, index):
        return self.board[index] == "0"

    def check_near_win(self, amount, player):
        positions = []
        for y in range(0, len(self.board)):
            if self.board[y] == str(player):
                positions.append(y)
        for z in self.winning_positions:
            if len(set(z) & set(positions)) == amount:
                return list(set(z) - set(positions))[0]

    def update_user_data(self, user, wins, losses, ties):
        with sqlite3.connect("database.db") as db:
            cursor = db.cursor()
            cursor.execute("UPDATE user_data SET wins = ?, losses = ?, ties = ? WHERE user_id = ?", (wins, losses, ties, user.id))