from models import Ticket, Round, RootData, session

import discord
import configparser
import logging
import os
import sqlalchemy
import lottery
from random import randint


handler = logging.StreamHandler()
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOGLEVEL", "INFO"))
logger.addHandler(handler)


class BotClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super(BotClient, self).__init__(*args, **kwargs)

        self.commands = {
            'help': self.help,

            'start': self.start_round,
            'end': self.end_round,
            'draw': self.draw_ticket,
            'echo': self.echo,
            'prizes': self.prizes,

            'search': self.search,

            'prefix': self.change_prefix,
        }

        self.config = configparser.SafeConfigParser()
        self.config.read('config.ini')


    async def on_ready(self):
        logger.info('Logged in as')
        logger.info(self.user.name)
        logger.info(self.user.id)
        logger.info(self.user.avatar)
        logger.info('------------')


    async def on_error(self, e, *a, **k):
        session.rollback()
        raise


    async def on_message(self, message):

        if message.author.bot or message.content is None or message.guild is None:
            return

        try:
            if await self.get_cmd(message):
                logger.info('Command: ' + message.content)
                session.commit()

        except discord.errors.Forbidden:
            try:
                await message.channel.send('No permissions to perform actions.')
            except discord.errors.Forbidden:
                logger.info('Twice Forbidden')


    async def get_cmd(self, message):

        data = session.query(RootData).first()
        if data is None:
            data = RootData(prefix='lotto ', prizes=[])
            session.add(data)
            session.commit()

            data = session.query(RootData).first()


        prefix = data.prefix

        command = None

        if message.content == self.user.mention:
            await self.commands['help'](message, '')

        if message.content[0:len(prefix)] == prefix:
            command = message.content[len(prefix):].split(' ')[0]
            stripped = message.content[len(command) + len(prefix):].strip()

        elif message.content[0:len(self.user.mention + ' ')] == self.user.mention + ' ':
            command = message.content[len(self.user.mention + ' '):].split(' ')[0]
            stripped = message.content[len(command) + len(self.user.mention + ' '):].strip()

        if command is not None:
            if command in self.commands.keys():
                await self.commands[command](message, stripped)

                return True

        return False


    async def help(self, message, stripped):
        data = session.query(RootData).first()

        await message.channel.send(embed=discord.Embed(title='Lottery Bot', description='''
`{0}start` - Start a drawing round
`{0}end` - End a drawing round
`{0}draw <mention>` - Draw a ticket for a user

`{0}search <type> [ID]` - Look for past draws

`{0}echo <message>` - Send a message as the bot
`{0}prefix <prefix>` - Change the bot's prefix
'''.format(data.prefix)))


    async def change_prefix(self, message, stripped):
        if message.author.guild_permissions.manage_guild:
            data = session.query(RootData).first()

            data.prefix = stripped
            await message.channel.send('Prefix updated to `{}`'.format(stripped))


    async def start_round(self, message, stripped):
        if message.author.guild_permissions.manage_guild:
            data = session.query(RootData).first()
            if data.prizes == []:
                await message.channel.send('You need to set your prizes before you continue. To do so please type `{}prizes`'.format(data.prefix))
                return
            round_ = session.query(Round).filter(Round.completed == False).first()
            if round_ is not None:
                await message.channel.send('There is already a round in progress. Please use `lotto end` to end the round.')

            else:
                r = Round(completed=False)
                session.add(r)
                session.commit()
                await message.channel.send('A round has been started! The Draw ID is **{}**'.format(r.id))


    async def end_round(self, message, stripped):
        if message.author.guild_permissions.manage_guild:
            round_ = session.query(Round).filter(Round.completed == False).first()
            data = session.query(RootData).first()
            if round_ is None:
                await message.channel.send('No round in progress. Use `lotto start` to start a round')

            else:
                round_.completed = True
                tickets = session.query(Ticket).filter(Ticket.round == round_.id)

                output = []
                prizes = data.prizes
                m = []

                for t in tickets:
                    matches, bonus = lottery.matches(round_.id, t.seed)
                    if matches > 0:
                        if (matches == 5 and bonus == True) \
                            or (matches == 1 and bonus == False) \
                            or (matches == 2 and bonus == False):
                            continue
                        else:
                            output.append([t, matches, bonus])
                    elif matches == 0 and bonus == True:
                        output.append([t, matches, bonus])

                await message.channel.send('The winning balls were: **{}**  **{}**  **{}**  **{}**  **{}**. The bonus was __{}__'.format(*lottery.gen_numbers(round_.id)))
                for n in output:
                    if n[2] == False:
                        m.append("<@{}> has won with {} matches! You have won {}".format(n[0].owner, n[1], prizes[n[1] - 1]))
                    else:
                        m.append("<@{}> has won with {} matches and a bonus ball! You have won {}".format(n[0].owner, n[1], prizes[n[1]]))

                sent = False
                current = ''
                for me in m:
                    if len(current + me) > 2000:
                        await message.channel.send(current)
                        sent = True
                        current = me
                    else:
                        current += me + '\n'

                if current or sent:
                    await message.channel.send(current)
                elif not sent:
                    await message.channel.send('No tickets matched the winning balls.')


    async def echo(self, message, stripped):
        if message.author.guild_permissions.manage_guild:

            await message.delete()
            await message.channel.send(stripped)


    async def draw_ticket(self, message, stripped):
        if message.author.guild_permissions.manage_guild:
            id_ = ''.join([x for x in stripped if x in '0123456789'])
            if id_ == '':
                await message.channel.send('Please mention a user to give the ticket to')

            else:
                m = message.guild.get_member(int(id_))
                if m is None:
                    await message.channel.send('Please mention a user to give the ticket to')

                else:
                    round_ = session.query(Round).filter(Round.completed == False).first()
                    if round_ is None:
                        await message.channel.send('No round has been started yet. Please wait for an admin to open tickets')

                    else:
                        t = Ticket(round=round_.id, owner=int(id_), seed=randint(0, 1000000000))
                        session.add(t)
                        session.commit()
                        await message.channel.send('{} has been given a new ticket (Ticket ID {}). The 5 numbers are: **{}  {}  {}  {}  {}**. The bonus is __{}__'.format(m.mention, t.id, *lottery.gen_numbers(t.seed)))


    async def search(self, message, stripped):
        args = [x for x in stripped.lower().split(' ') if x]

        if not (len(args) == 0 or (len(args) == 2 and args[0] in ['rounds', 'tickets'])):
            await message.channel.send('Please specify what to search for (`rounds` or `tickets`)')

        else:
            if len(args) == 0:
                await message.channel.send('A total of {} rounds have occurred. To get more information, type `lotto search <rounds/tickets> <ID>`'.format(session.query(Round).count()))
                m = ''
                for r in session.query(Round).filter(Round.completed == True):
                    t = session.query(Ticket).filter(Ticket.round == r.id).order_by(Ticket.id)
                    s = '''**{:02d}:** Numbers: `{:02d} {:02d} {:02d} {:02d} {:02d}   {:02d}`. Ticket IDs: `{}-{}`\n'''.format(
                        r.id,
                        *lottery.gen_numbers(r.id),
                        t.first().id,
                        t.all()[-1].id)

                    if len(m + s) > 2000:
                        await message.channel.send(m)
                        m = s
                    else:
                        m += s

                await message.channel.send(m)

            else:
                type_ = args[0]
                id_ = args[1]
                if not all(x in '0123456789' for x in id_):
                    await message.channel.send('Please specify an integer ID')

                elif type_ == 'rounds':
                    r = session.query(Round).get(int(id_))
                    tickets = session.query(Ticket).filter(Ticket.round == int(id_))

                    s = '''**Round {:02d}:**
    Numbers: `{:02d} {:02d} {:02d} {:02d} {:02d}   {:02d}`.
    Ticket IDs: `{}-{}`\n'''.format(
                        r.id,
                        *lottery.gen_numbers(r.id),
                        tickets.first().id,
                        tickets.all()[-1].id)

                    for t in tickets:
                        m = '''**Ticket ID: {}**
    Numbers: `{:02d} {:02d} {:02d} {:02d} {:02d}   {:02d}`
    Owner: <@{}>
    Matches: **{}**
    Bonus: **{}**\n'''.format(
        t.id,
        *lottery.gen_numbers(t.seed),
        t.owner,
        *lottery.matches(t.seed, r.id))

                        if len(s + m) > 2000:
                            await message.channel.send(s)
                            s = m
                        else:
                            s += m

                    await message.channel.send(s)

                elif type_ == 'tickets':
                    s = session.query(Ticket).get(int(id_))
                    if s is None:
                        await message.channel.send('That ticket couldn\'t be found.')
                    else:
                        await message.channel.send('Owner: <@{}>. Numbers: `{:02d} {:02d} {:02d} {:02d} {:02d}   {:02d}`. Round: `{:02d}`'.format(s.owner, *lottery.gen_numbers(s.seed), s.round))


    async def prizes(self, message, stripped):
        if message.author.guild_permissions.administrator:
            data = session.query(RootData).first()
            combinations = ['5 Balls + Bonus Ball', '5 Balls', '4 Balls + Bonus Ball', '4 Balls', '3 Balls + Bonus Ball', '3 Balls', '2 Balls + Bonus Ball', '1 Ball + Bonus Ball', 'Just the Bonus Ball']
            await message.channel.send('When prompted, please enter the prize for the specific win combination (type "cancel" to cancel the setup):')
            oldList = data.prizes
            data.prizes = []
            for n in range(1,10):
                print(n)
                await message.channel.send(combinations[n - 1] + ':')
                response = await client.wait_for('message', check=lambda m: m.author == message.author and m.channel == message.channel)
                if response.content == "cancel":
                    data.prizes = oldList
                    session.commit()
                    await message.channel.send('Prize setup cancelled')
                    return
                data.prizes.append(response.content)
            session.commit()
            await message.channel.send('Prizes Set')


client = BotClient()

client.run(client.config.get('DEFAULT', 'token'))
