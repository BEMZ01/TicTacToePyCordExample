# cog to implement a tictactoe game
from os import path, mkdir
import random as r
import discord
from discord.ext import commands
from discord import Member
from discord.commands import Option
import asyncio
import pandas as pd
import threading


class Queue:
    def __init__(self):
        self.queue = []
        self.tail = 0
        self.length = 0

    def put(self, item):
        self.queue.append(item)
        self.tail += 1
        self.length = len(self.queue)

    def get(self):
        if self.length > 0:
            self.length -= 1
            return self.queue.pop(0)
        else:
            return None

    def peek(self):
        if self.length > 0:
            return self.queue[0]
        else:
            return None


Bot = ""


def setup(bot):
    global Bot
    Bot = bot
    if not path.isfile("data/pvp_scoreboard.csv") and not path.isfile("data/bot_scoreboard.csv"):
        if not path.isdir("data"):
            mkdir("data")
        with open("data/pvp_scoreboard.csv", "w") as f:
            f.write("account_id,wins,losses,ties\n")
        with open("data/bot_scoreboard.csv", "w") as f:
            f.write("account_id,wins,losses,ties\n")
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


def get_user_stats(userid: int, table: str):
    df = pd.read_csv(f"data/{table}.csv")
    df = df[df["account_id"] == userid]
    if df.empty:
        return False, None
    return True, df.to_dict("records")[0]


def update_user_data(userid: int, wins: int, losses: int, ties: int, table: str):
    df = pd.read_csv(f"data/{table}.csv")
    df = df[df["account_id"] == userid]
    if df.empty:
        df = df.concat({"account_id": userid, "wins": wins, "losses": losses, "ties": ties}, ignore_index=True)
    else:
        df["wins"] = wins
        df["losses"] = losses
        df["ties"] = ties
    df.to_csv(f"data/{table}.csv", index=False)


def does_user_exist(userid: int, table: str):
    df = pd.read_csv(f"data/{table}.csv")
    df = df[df["account_id"] == userid]
    if df.empty:
        return False
    return True


async def add_message_emojis(message):
    for x in ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]:
        await message.add_reaction(x)


class TicTacToe(commands.Cog, name="TicTacToe Game"):
    def __init__(self, bot):
        self.searching = Queue()
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
        self._SearchManager(threading.Event())
        self.games = []

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
            await ctx.respond(f"Waiting for {player2.name} to accept...", delete_after=30, ephemeral=True)
            message = await ctx.channel.send(f"{player2.mention} do you accept this challenge?", delete_after=30)
            await message.add_reaction("✅")
            await message.add_reaction("❌")
            try:
                reaction, user = await self.bot.wait_for("reaction_add", check=self.check_p2_check, timeout=30)
            except asyncio.TimeoutError:
                await message.channel.send("Game stopped due to inactivity.", delete_after=10)
                return
            if reaction:
                await message.delete()
                if str(reaction) == "✅":
                    self.turn = r.choice([1, 2])
                    self.game_message_id = await ctx.send(
                        f"Starting game between {self.player1.name} and {self.player2.name}!")
                    await self.add_emoijs()
                    await self.update_board()
                    while True:
                        if self.turn == 1:
                            try:
                                reaction, user = await self.bot.wait_for("reaction_add", check=self.check_p1_turn,
                                                                         timeout=30)
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
                                    # check if the user is playing themselves
                                    if self.player1.id != self.player2.id:
                                        # update player1 stats
                                        if get_user_stats(self.player1.id, "pvp_scoreboard")[1] is not None:
                                            success, result = get_user_stats(self.player1.id, "pvp_scoreboard")
                                            if success:
                                                wins, losses, ties = (result["wins"], result["losses"], result["ties"])
                                                wins += 1
                                                update_user_data(self.player1.id, wins, losses, ties, "pvp_scoreboard")
                                        else:
                                            update_user_data(self.player1.id, 1, 0, 0, "pvp_scoreboard")
                                        # update player2 stats
                                        if get_user_stats(self.player2.id, "pvp_scoreboard")[1] is not None:
                                            success, result = get_user_stats(self.player2.id, "pvp_scoreboard")
                                            if success:
                                                wins, losses, ties = (result["wins"], result["losses"], result["ties"])
                                                losses += 1
                                                update_user_data(self.player2.id, wins, losses, ties, "pvp_scoreboard")
                                        else:
                                            update_user_data(self.player2.id, 0, 1, 0, "pvp_scoreboard")
                                    await self.game_message_id.clear_reactions()
                                    self.game_message_id = None
                                    self.board = ["0", "0", "0", "0", "0", "0", "0", "0", "0"]
                                    return
                                elif self.check_win() == -1:
                                    await self.game_message_id.edit(f"🎉* Nice Draw!*🎉",
                                                                    delete_after=15)
                                    # check if the user is playing themselves
                                    if self.player1.id != self.player2.id:
                                        # update player1 stats
                                        if get_user_stats(self.player1.id, "pvp_scoreboard")[1] is not None:
                                            success, result = get_user_stats(self.player1.id, "pvp_scoreboard")
                                            if success:
                                                wins, losses, ties = (result["wins"], result["losses"], result["ties"])
                                                ties += 1
                                                update_user_data(self.player1.id, wins, losses, ties, "pvp_scoreboard")
                                        else:
                                            update_user_data(self.player1.id, 0, 0, 1, "pvp_scoreboard")
                                        # update player2 stats
                                        if get_user_stats(self.player2.id, "pvp_scoreboard")[1] is not None:
                                            success, result = get_user_stats(self.player2.id, "pvp_scoreboard")
                                            if success:
                                                wins, losses, ties = (result["wins"], result["losses"], result["ties"])
                                                ties += 1
                                                update_user_data(self.player2.id, wins, losses, ties, "pvp_scoreboard")
                                        else:
                                            update_user_data(self.player2.id, 0, 0, 1, "pvp_scoreboard")
                                    await self.game_message_id.clear_reactions()
                                    self.game_message_id = None
                                    self.board = ["0", "0", "0", "0", "0", "0", "0", "0", "0"]
                                    return
                            await self.game_message_id.remove_reaction(reaction, user)
                            await self.game_message_id.add_reaction(reaction)
                        elif self.turn == 2:
                            try:
                                reaction, user = await self.bot.wait_for("reaction_add", check=self.check_p2_turn,
                                                                         timeout=30)
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
                                    # check if the user is playing themselves
                                    if self.player1.id != self.player2.id:
                                        # update player1 stats
                                        if get_user_stats(self.player1.id, "pvp_scoreboard")[1] is not None:
                                            success, result = get_user_stats(self.player1.id, "pvp_scoreboard")
                                            if success:
                                                wins, losses, ties = (result["wins"], result["losses"], result["ties"])
                                                losses += 1
                                                update_user_data(self.player1.id, wins, losses, ties, "pvp_scoreboard")
                                        else:
                                            update_user_data(self.player1.id, 0, 1, 0, "pvp_scoreboard")
                                        # update player2 stats
                                        if get_user_stats(self.player2.id, "pvp_scoreboard")[1] is not None:
                                            success, result = get_user_stats(self.player2.id, "pvp_scoreboard")
                                            if success:
                                                wins, losses, ties = (result["wins"], result["losses"], result["ties"])
                                                wins += 1
                                                update_user_data(self.player2.id, wins, losses, ties, "pvp_scoreboard")
                                        else:
                                            update_user_data(self.player2.id, 1, 0, 0, "pvp_scoreboard")
                                    await self.game_message_id.clear_reactions()
                                    self.game_message_id = None
                                    self.board = ["0", "0", "0", "0", "0", "0", "0", "0", "0"]
                                    return
                                elif self.check_win() == -1:
                                    await self.game_message_id.edit(f"🎉* Nice Draw!*🎉",
                                                                    delete_after=15)
                                    # check if the user is playing themselves
                                    if self.player1.id != self.player2.id:
                                        # update player1 stats
                                        if get_user_stats(self.player1.id, "pvp_scoreboard")[1] is not None:
                                            success, result = get_user_stats(self.player1.id, "pvp_scoreboard")
                                            if success:
                                                wins, losses, ties = (result["wins"], result["losses"], result["ties"])
                                                ties += 1
                                                update_user_data(self.player1.id, wins, losses, ties, "pvp_scoreboard")
                                        else:
                                            update_user_data(self.player1.id, 0, 0, 1, "pvp_scoreboard")
                                        # update player2 stats
                                        if get_user_stats(self.player2.id, "pvp_scoreboard")[1] is not None:
                                            success, result = get_user_stats(self.player2.id, "pvp_scoreboard")
                                            if success:
                                                wins, losses, ties = (result["wins"], result["losses"], result["ties"])
                                                ties += 1
                                                update_user_data(self.player2.id, wins, losses, ties, "pvp_scoreboard")
                                        else:
                                            update_user_data(self.player2.id, 0, 0, 1, "pvp_scoreboard")
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
            self.turn = r.choice([1, 2])
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
                            if does_user_exist(self.player1.id, "bot_scoreboard"):
                                success, result = get_user_stats(self.player1.id, "bot_scoreboard")
                                if success:
                                    wins, losses, ties = (result["wins"], result["losses"], result["ties"])
                                    wins += 1
                                    update_user_data(self.player1.id, wins, losses, ties, "bot_scoreboard")
                            else:
                                update_user_data(self.player1.id, 1, 0, 0, "bot_scoreboard")
                            await self.game_message_id.clear_reactions()
                            self.game_message_id = None
                            self.board = ["0", "0", "0", "0", "0", "0", "0", "0", "0"]
                            return
                        elif self.check_win() == -1:
                            await self.game_message_id.edit(f"🎉* Nice Draw!*🎉",
                                                            delete_after=15)
                            if self.player1.id != self.player2:
                                # update player1 stats
                                if get_user_stats(self.player1.id, "bot_scoreboard")[1] is not None:
                                    success, result = get_user_stats(self.player1.id, "bot_scoreboard")
                                    if success:
                                        wins, losses, ties = (result["wins"], result["losses"], result["ties"])
                                        ties += 1
                                        update_user_data(self.player1.id, wins, losses, ties, "bot_scoreboard")
                                else:
                                    update_user_data(self.player1.id, 0, 0, 1, "bot_scoreboard")
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
                        if self.player1.id != self.player2:
                            # update player1 stats
                            if get_user_stats(self.player1.id, "bot_scoreboard")[1] is not None:
                                success, result = get_user_stats(self.player1.id, "bot_scoreboard")
                                if success:
                                    wins, losses, ties = (result["wins"], result["losses"], result["ties"])
                                    ties += 1
                                    update_user_data(self.player1.id, wins, losses, ties, "bot_scoreboard")
                            else:
                                update_user_data(self.player1.id, 0, 0, 1, "bot_scoreboard")
                        await self.game_message_id.clear_reactions()
                        self.game_message_id = None
                        self.board = ["0", "0", "0", "0", "0", "0", "0", "0", "0"]
                        return

    async def ai_turn(self):
        bias = r.choice([0, 1])
        if bias == 0:  # prefer to win
            if not self.check_near_win(2, 2) is None:
                index = self.check_near_win(2, 2)
                if self.check_ai_colision(index):
                    print("winning at position " + str(self.check_near_win(2, 2)))
                    self.board[index] = "2"
                    return
                else:
                    self.board[r.choice(self.get_empty_positions())] = "2"
                    return
            elif not self.check_near_win(2, 1) is None:
                index = self.check_near_win(2, 1)
                if self.check_ai_colision(index):
                    print("blocking at position " + str(index))
                    self.board[index] = "2"
                    return
                else:
                    self.board[r.choice(self.get_empty_positions())] = "2"
                    return
        if bias == 1:  # prefer to block
            if not self.check_near_win(2, 1) is None:
                index = self.check_near_win(2, 1)
                if self.check_ai_colision(index):
                    print("blocking at position " + str(index))
                    self.board[index] = "2"
                    return
                else:
                    self.board[r.choice(self.get_empty_positions())] = "2"
                    return
            elif not self.check_near_win(2, 2) is None:
                index = self.check_near_win(2, 2)
                if self.check_ai_colision(index):
                    print("winning at position " + str(self.check_near_win(2, 2)))
                    self.board[index] = "2"
                    return
                else:
                    self.board[r.choice(self.get_empty_positions())] = "2"
                    return
        # if no near win, play a random move
        while True:
            move = r.randint(0, 8)
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

    async def update_message_board(self, message):
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
        await message.edit(embed=embed)

    async def add_emoijs(self):
        for x in ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]:
            await self.game_message_id.add_reaction(x)

    def check_p1_turn(self, reaction, user):
        return str(user) == str(self.player1) and str(reaction) in ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣",
                                                                    "8️⃣", "9️⃣"]

    def check_p2_turn(self, reaction, user):
        return str(user) == str(self.player2) and str(reaction) in ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣",
                                                                    "8️⃣", "9️⃣"]

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

    @discord.slash_command(name="scorecard", description="Shows the scoreboard when playing vs bots.")
    async def scorecard(self, ctx, scoreboard: Option(int, "1. Vs Computer Scoreboard, 2. PvP Scoreboard"),
                        user: Option(discord.Member, "A User to show the scoreboard of.", required=False)):
        await ctx.defer()
        if scoreboard == 1:
            if user is None:
                user = ctx.author
            data = get_user_stats(user.id, "bot_scoreboard")
            if data[0]:
                embed = discord.Embed(title="Scoreboard", description=f"Showing the scoreboard for {user.name}",
                                      color=discord.Color.from_rgb(r.randint(0, 255), r.randint(0, 255),
                                                                   r.randint(0, 255)))
                embed.add_field(name="Wins", value=data[1]["wins"])
                embed.add_field(name="Losses", value=data[1]["losses"])
                embed.add_field(name="Draws", value=data[1]["ties"])
                embed.add_field(name="Total Games",
                                value=int(data[1]["wins"]) + int(data[1]["losses"]) + int(data[1]["ties"]))
                embed.add_field(name="Win Rate",
                                value=f"{round((int(data[1]['wins']) / (int(data[1]['wins']) + int(data[1]['losses']) + int(data[1]['ties']))) * 100, 2)}%")
                await ctx.respond(embed=embed, delete_after=30)
            else:
                await ctx.respond(f"No data found for {user.name}.", delete_after=30)
        elif scoreboard == 2:
            if user is None:
                user = ctx.author
            data = get_user_stats(user.id, "pvp_scoreboard")
            if data[0]:
                embed = discord.Embed(title="Scoreboard", description=f"Showing the scoreboard for {user.name}",
                                      color=discord.Color.from_rgb(r.randint(0, 255), r.randint(0, 255),
                                                                   r.randint(0, 255)))
                embed.add_field(name="Wins", value=data[1]["wins"])
                embed.add_field(name="Losses", value=data[1]["losses"])
                embed.add_field(name="Draws", value=data[1]["ties"])
                embed.add_field(name="Total Games",
                                value=int(data[1]["wins"]) + int(data[1]["losses"]) + int(data[1]["ties"]))
                embed.add_field(name="Win Rate",
                                value=f"{round((int(data[1]['wins']) / (int(data[1]['wins']) + int(data[1]['losses']) + int(data[1]['ties']))) * 100, 2)}%")
                await ctx.respond(embed=embed, delete_after=30)
            else:
                await ctx.respond(f"No data found for {user.name}.", delete_after=30)
        else:
            await ctx.respond(
                "Invalid scoreboard type. Please use 1 to see Bot scoreboard or 2 to see player scoreboard.",
                delete_after=30)

    @discord.slash_command(name="search", description="Searches for a match with someone not in your server.")
    async def search(self, ctx):
        await ctx.defer()
        if ctx.author in self.searching.queue:
            self.searching.queue.remove(ctx.author)
            await ctx.respond("You have been removed from the search queue.", delete_after=30)
        else:
            self.searching.put(ctx.author)
            await ctx.respond("Searching for a match...", delete_after=30)

    def _SearchManager(self, f_stop):
        # do something here ...
        print("CHECKING QUEUE FOR PLAYERS")
        if self.searching.length >= 2:
            player1 = self.searching.get()
            player2 = self.searching.get()
            self.games.append(MultiplayerTTT(self.bot, player1, player2))

            ###
            if not f_stop.is_set():
                # call f() again in 5 seconds
                threading.Timer(5, self.SearchManager, [f_stop]).start()


class MultiplayerTTT(commands.Cog, name="Multiplayer module for Tic Tac Toe"):
    def __init__(self, bot, player1, player2):
        self.bot = bot
        self.player1 = player1
        self.player2 = player2
        self.board = ["0", "0", "0", "0", "0", "0", "0", "0", "0"]
        self.winning_positions = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [0, 3, 6], [1, 4, 7], [2, 5, 8], [0, 4, 8],
                                  [2, 4, 6]]
        self.emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]

    async def _PrivateGame(self, player1, player2):
        # DM player1 and player2 to ask if they want to play a private game
        self.player1_game = player1.send(
            f"A Match has been found. You are playing against {player2.name}. Please wait...")
        self.player2_game = player2.send(
            f"A Match has been found. You are playing against {player1.name}. Please wait...")
        await add_message_emojis(self.player1_game)
        await add_message_emojis(self.player2_game)
        await self.update_message_board(self.player1_game)
        await self.update_message_board(self.player2_game)
        self.turn = r.choice([1, 2])
        while 1:
            if self.turn == 1:
                try:
                    reaction, user = await self.bot.wait_for("reaction_add", check=self.check_p1_check, timeout=30)
                except asyncio.TimeoutError:
                    await self.player1_game.edit(content="Game timed out.")
                    await self.player2_game.edit(content="Game timed out.")
                    break
                if reaction and self.check_colision(reaction):
                    self.board[int(str(reaction)[0]) - 1] = "1"
                    self.turn = 2
                    await self.update_board()
                    if self.check_win() == 1:
                        await self.game_message_id.edit(f"🎉* {self.player1.name} (Player 1) won!*🎉",
                                                        delete_after=15)
                        # check if the user is playing themselves
                        if self.player1.id != self.player2.id:
                            # update player1 stats
                            if get_user_stats(self.player1.id, "pvp_scoreboard")[1] is not None:
                                success, result = get_user_stats(self.player1.id, "pvp_scoreboard")
                                if success:
                                    wins, losses, ties = (result["wins"], result["losses"], result["ties"])
                                    wins += 1
                                    update_user_data(self.player1.id, wins, losses, ties, "pvp_scoreboard")
                            else:
                                update_user_data(self.player1.id, 1, 0, 0, "pvp_scoreboard")
                            # update player2 stats
                            if get_user_stats(self.player2.id, "pvp_scoreboard")[1] is not None:
                                success, result = get_user_stats(self.player2.id, "pvp_scoreboard")
                                if success:
                                    wins, losses, ties = (result["wins"], result["losses"], result["ties"])
                                    losses += 1
                                    update_user_data(self.player2.id, wins, losses, ties, "pvp_scoreboard")
                            else:
                                update_user_data(self.player2.id, 0, 1, 0, "pvp_scoreboard")
                        await self.game_message_id.clear_reactions()
                        self.game_message_id = None
                        self.board = ["0", "0", "0", "0", "0", "0", "0", "0", "0"]
                        return
                    elif self.check_win() == -1:
                        await self.game_message_id.edit(f"🎉* Nice Draw!*🎉",
                                                        delete_after=15)
                        # check if the user is playing themselves
                        if self.player1.id != self.player2.id:
                            # update player1 stats
                            if get_user_stats(self.player1.id, "pvp_scoreboard")[1] is not None:
                                success, result = get_user_stats(self.player1.id, "pvp_scoreboard")
                                if success:
                                    wins, losses, ties = (result["wins"], result["losses"], result["ties"])
                                    ties += 1
                                    update_user_data(self.player1.id, wins, losses, ties, "pvp_scoreboard")
                            else:
                                update_user_data(self.player1.id, 0, 0, 1, "pvp_scoreboard")
                            # update player2 stats
                            if get_user_stats(self.player2.id, "pvp_scoreboard")[1] is not None:
                                success, result = get_user_stats(self.player2.id, "pvp_scoreboard")
                                if success:
                                    wins, losses, ties = (result["wins"], result["losses"], result["ties"])
                                    ties += 1
                                    update_user_data(self.player2.id, wins, losses, ties, "pvp_scoreboard")
                            else:
                                update_user_data(self.player2.id, 0, 0, 1, "pvp_scoreboard")
                        await self.game_message_id.clear_reactions()
                        self.game_message_id = None
                        self.board = ["0", "0", "0", "0", "0", "0", "0", "0", "0"]
                        return
                await self.game_message_id.remove_reaction(reaction, user)
                await self.game_message_id.add_reaction(reaction)

    def check_p2_check(self, reaction, user):
        return str(user) == str(self.player2) and str(reaction.emoji) == str(reaction)

    def check_p1_check(self, reaction, user):
        return str(user) == str(self.player1) and str(reaction.emoji) == str(reaction)

    def check_colision(self, reaction):
        if self.board[int(str(reaction)[0]) - 1] == "0":
            return True
        else:
            return False

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
        if "0" not in self.board:
            return True
        else:
            return False
