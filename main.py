import discord
from discord import app_commands
import json
import asyncio
import io
from pathlib import Path

with open('config.json') as f:
    config = json.load(f)

GUILD_ID = int(config['guildid'])
DATA_PATH     = Path('data/buttonCategories.json')
SETTINGS_PATH = Path('data/settings.json')

TICKET_TYPES = {
    'denuncias': {
        'label': 'Denúncias',
        'emoji': '🚨',
        'description': 'Denuncia um user ou conteúdo enviado para o servidor',
        'confirm_msg': (
            'Se quiseres fazer uma denúncia reúne :\n\n'
            '» provas do ocorrido\n'
            '» @discord de pessoas em questão\n'
            '» descrição do ocorrido\n\n'
            '**Vamos responder o mais rápido possível!**'
        ),
        'welcome_lines': [
            '- Descreve a situação que pretendes denunciar',
            '- Inclui provas (capturas de ecrã, links, etc.)',
            '- Indica o utilizador envolvido, se aplicável',
        ],
    },
    'geral': {
        'label': 'Geral',
        'emoji': '💬',
        'description': 'Dúvidas gerais',
        'confirm_msg': (
            'Nesta sala podes tirar todas as dúvidas gerais\n\n'
            'Se quiseres abrir um ticket de dúvidas gerais explica bem o teu problema e '
            'certifica-te que a resposta não existe no servidor.\n\n'
            '**Vamos responder o mais rápido possível!**'
        ),
        'welcome_lines': [
            '- Descreve o teu assunto detalhadamente',
            '- A equipa responderá o mais rápido possível',
        ],
    },
    'printer': {
        'label': 'Printer',
        'emoji': '💸',
        'description': 'Recebe a role @printer',
        'confirm_msg': (
            'Se quiseres receber a Role @Printer carrega no botão em baixo para abrir ticket e '
            'Garante que fizeste 1 dos 4 requisitos:\n\n'
            '» Ter conta criada na MEXC pelo nosso link e fazer volume mensalmente\n'
            '» Ter conta no ATAS criada pelo nosso link e ter aderido a um dos planos\n'
            '» Usaste o nosso código de desconto "AP" em alguma PropFirm com que tenhamos parceria\n'
            '» Entraste Na Mentoria do Pereira ou do Raúl'
        ),
        'welcome_lines': [
            '- Garante que fizeste 1 dos 4 requisitos:',
            '- Ter conta criada na MEXC pelo nosso link e fazer volume mensalmente',
            '- Ter conta no ATAS criada pelo nosso link e ter aderido a um dos planos',
            '- Usaste o nosso código de desconto "AP" em alguma PropFirm com que tenhamos parceria',
            '- Entraste Na Mentoria do Pereira ou do Raúl',
        ],
    },
    'sugestoes': {
        'label': 'Sugestões',
        'emoji': '💡',
        'description': 'Faz uma sugestão para melhorar o servidor',
        'confirm_msg': (
            'Tens uma ideia para melhorar o servidor?\n\n'
            'Sugerir funcionalidades, eventos ou melhorias é sempre bem-vindo! '
            'Partilha a tua sugestão de forma clara e detalhada.\n\n'
            '**Vamos responder o mais rápido possível!**'
        ),
        'welcome_lines': [
            '- Descreve a tua sugestão detalhadamente',
            '- Explica como isso beneficiaria a comunidade',
        ],
    },
    'mentorship': {
        'label': 'Mentorship',
        'emoji': '📚',
        'description': 'Interessa-te por uma das nossas mentorias',
        'confirm_msg': (
            'Se estás interessado em entrar em uma Mentorship, clica no botão em baixo '
            'e específica no ticket qual tens interesse.\n\n'
            '**Vamos responder o mais rápido possível!**'
        ),
        'welcome_lines': [
            '- diz nos qual mentoria tens intenção de comprar',
            '- Indica qualquer dúvida que tenhas sobre a mentorship',
        ],
    },
}


# ── Data helpers ──────────────────────────────────────────────────────────────

def load_button_categories():
    if not DATA_PATH.exists():
        return {}
    return json.loads(DATA_PATH.read_text())

def save_button_categories(data):
    DATA_PATH.parent.mkdir(exist_ok=True)
    DATA_PATH.write_text(json.dumps(data, indent=2))

def get_category_id(button_key):
    data = load_button_categories()
    if button_key in data:
        return int(data[button_key])
    raw = config['tickets'].get('categoryId', '').strip()
    return int(raw) if raw else None

def load_settings():
    if not SETTINGS_PATH.exists():
        return {}
    return json.loads(SETTINGS_PATH.read_text())

def save_settings(data):
    SETTINGS_PATH.parent.mkdir(exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(data, indent=2))


# ── Transcript ────────────────────────────────────────────────────────────────

async def create_transcript(channel: discord.TextChannel) -> discord.File:
    lines = [f'Transcrito — #{channel.name}\n{"=" * 50}']
    async for msg in channel.history(limit=500, oldest_first=True):
        ts = msg.created_at.strftime('%d/%m/%Y %H:%M:%S')
        content = msg.content or ''
        for emb in msg.embeds:
            parts = [emb.title or '', emb.description or '']
            content += ' '.join(p for p in parts if p)
        for att in msg.attachments:
            content += f' [Anexo: {att.url}]'
        lines.append(f'[{ts}] {msg.author.display_name}: {content}')
    data = '\n'.join(lines).encode('utf-8')
    return discord.File(fp=io.BytesIO(data), filename=f'transcript-{channel.name}.txt')


# ── Views ─────────────────────────────────────────────────────────────────────

class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=t['label'],
                value=key,
                description=t['description'],
                emoji=t['emoji'],
            )
            for key, t in TICKET_TYPES.items()
        ]
        super().__init__(
            placeholder='Seleciona uma categoria...',
            options=options,
            custom_id='ticket_select',
        )

    async def callback(self, interaction: discord.Interaction):
        key = self.values[0]
        t = TICKET_TYPES[key]
        embed = discord.Embed(
            title=f"{t['emoji']} {t['label']}",
            description=t['confirm_msg'],
            color=0xE74C3C,
        )
        await interaction.response.send_message(embed=embed, view=ConfirmView(key), ephemeral=True)


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())


class ConfirmView(discord.ui.View):
    def __init__(self, key: str):
        super().__init__(timeout=120)
        self.key = key

    @discord.ui.button(label='Abrir ticket', emoji='📋', style=discord.ButtonStyle.primary)
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        guild  = interaction.guild
        member = interaction.user
        t = TICKET_TYPES[self.key]

        existing = discord.utils.find(
            lambda ch: ch.topic and f'uid:{member.id}' in ch.topic,
            guild.text_channels,
        )
        if existing:
            await interaction.followup.send(f'❌ Já tens um ticket aberto: {existing.mention}', ephemeral=True)
            return

        safe_name = ''.join(c for c in member.name.lower() if c.isalnum())[:20] or str(member.id)
        cat_id    = get_category_id(self.key)
        category  = guild.get_channel(cat_id) if cat_id else None

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(
                view_channel=True, send_messages=True,
                read_message_history=True, attach_files=True,
            ),
        }
        for role_id in config['tickets']['supportRoleIds']:
            role = guild.get_role(int(role_id))
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True,
                    read_message_history=True, manage_messages=True, attach_files=True,
                )

        channel = await guild.create_text_channel(
            name=f'ticket-{safe_name}',
            category=category,
            topic=f"{t['label']} | uid:{member.id} | {member.name}",
            overwrites=overwrites,
        )

        bullet_text = '\n' + '\n'.join(t['welcome_lines'])
        embed = discord.Embed(
            title=f"{t['emoji']} Ticket — {t['label']}",
            description=(
                f"Olá {member.mention}! A equipa irá atender-te em breve.\n\n"
                f"**Por favor fornece as seguintes informações:**{bullet_text}"
            ),
            color=0xE74C3C,
        )
        embed.set_footer(text='Clica em "Fechar Ticket" quando o assunto estiver resolvido.')

        await channel.send(content=member.mention, embed=embed, view=CloseTicketView())
        await interaction.followup.send(f'✅ Ticket criado: {channel.mention}', ephemeral=True)

        log_id = config['tickets'].get('logChannelId', '').strip()
        if log_id:
            log_ch = guild.get_channel(int(log_id))
            if log_ch:
                log_embed = discord.Embed(title='🎫 Ticket Aberto', color=0x00FF00)
                log_embed.add_field(name='Utilizador', value=f'{member.mention} ({member.name})', inline=True)
                log_embed.add_field(name='Categoria',  value=f"{t['emoji']} {t['label']}",        inline=True)
                log_embed.add_field(name='Canal',      value=channel.mention,                      inline=True)
                await log_ch.send(embed=log_embed)


class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Fechar Ticket', emoji='🔒', style=discord.ButtonStyle.danger, custom_id='ticket_close')
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(description='🔒 O ticket será fechado em 5 segundos...', color=0xFF0000)
        await interaction.response.send_message(embed=embed)

        # Transcript
        settings = load_settings()
        transcript_id = settings.get('transcriptChannelId', '').strip()
        if not transcript_id:
            transcript_id = config['tickets'].get('transcriptChannelId', '').strip()
        if transcript_id:
            transcript_ch = interaction.guild.get_channel(int(transcript_id))
            if transcript_ch:
                transcript_file = await create_transcript(interaction.channel)
                t_embed = discord.Embed(
                    title='📄 Transcrito do Ticket',
                    description=(
                        f'**Canal:** #{interaction.channel.name}\n'
                        f'**Fechado por:** {interaction.user.mention}'
                    ),
                    color=0xE74C3C,
                )
                await transcript_ch.send(embed=t_embed, file=transcript_file)

        # Log
        log_id = config['tickets'].get('logChannelId', '').strip()
        if log_id:
            log_ch = interaction.guild.get_channel(int(log_id))
            if log_ch:
                log_embed = discord.Embed(title='🔒 Ticket Fechado', color=0xFF0000)
                log_embed.add_field(name='Canal',      value=interaction.channel.name,  inline=True)
                log_embed.add_field(name='Fechado por', value=interaction.user.mention, inline=True)
                await log_ch.send(embed=log_embed)

        await asyncio.sleep(5)
        await interaction.channel.delete()


# ── Bot setup ─────────────────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.members = True

bot  = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)


@bot.event
async def on_ready():
    print(f'✅ Bot conectado como: {bot.user}')
    bot.add_view(TicketPanelView())
    bot.add_view(CloseTicketView())
    try:
        synced = await tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f'✅ {len(synced)} comando(s) registado(s).')
    except Exception as e:
        print(f'❌ Erro ao registar comandos: {e}')


# ── Slash commands ─────────────────────────────────────────────────────────────

@tree.command(name='setup', description='Cria o painel de tickets neste canal', guild=discord.Object(id=GUILD_ID))
@app_commands.default_permissions(manage_channels=True)
async def setup(interaction: discord.Interaction):
    settings = load_settings()
    embed = discord.Embed(
        title='Central de Suporte Alpha Print',
        description=(
            'Nesta sala podes tirar todas as dúvidas e entrar em contacto com a equipa da Alpha Print\n'
            'Para evitar Problemas, por favor lê com atenção todas as opções e explica sempre o motivo do ticket\n\n'
            'A equipa irá fechar o ticket se:\n'
            '» Não houver uma resposta até 48H\n'
            '» O motivo não for válido'
        ),
        color=0xE74C3C,
    )
    image_url = settings.get('panelImage', '')
    if image_url:
        embed.set_image(url=image_url)
    await interaction.channel.send(embed=embed, view=TicketPanelView())
    await interaction.response.send_message('✅ Painel de tickets criado!', ephemeral=True)


@tree.command(
    name='setcategoria',
    description='Define em que categoria do Discord cada opção de ticket abre os tickets',
    guild=discord.Object(id=GUILD_ID),
)
@app_commands.default_permissions(manage_channels=True)
@app_commands.describe(botao='Opção de ticket a configurar', categoria='Categoria do Discord')
@app_commands.choices(botao=[
    app_commands.Choice(name='🚨 Denúncias',  value='denuncias'),
    app_commands.Choice(name='💬 Geral',       value='geral'),
    app_commands.Choice(name='🖨️ Printer',    value='printer'),
    app_commands.Choice(name='💡 Sugestões',   value='sugestoes'),
    app_commands.Choice(name='📚 Mentorship',  value='mentorship'),
])
async def setcategoria(interaction: discord.Interaction, botao: str, categoria: discord.CategoryChannel):
    data = load_button_categories()
    data[botao] = str(categoria.id)
    save_button_categories(data)
    t = TICKET_TYPES[botao]
    embed = discord.Embed(
        title='✅ Categoria Definida',
        description=f"Os tickets de **{t['emoji']} {t['label']}** serão criados na categoria **{categoria.name}**.",
        color=0x00FF00,
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(
    name='settranscript',
    description='Define o canal onde os transcritos dos tickets são enviados automaticamente',
    guild=discord.Object(id=GUILD_ID),
)
@app_commands.default_permissions(manage_channels=True)
@app_commands.describe(canal='Canal de texto para onde os transcritos serão enviados')
async def settranscript(interaction: discord.Interaction, canal: discord.TextChannel):
    settings = load_settings()
    settings['transcriptChannelId'] = str(canal.id)
    save_settings(settings)
    embed = discord.Embed(
        title='✅ Canal de Transcritos Definido',
        description=f'Os transcritos dos tickets serão enviados para {canal.mention}.',
        color=0x00FF00,
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(
    name='setimagem',
    description='Define a imagem de fundo do painel de tickets',
    guild=discord.Object(id=GUILD_ID),
)
@app_commands.default_permissions(manage_channels=True)
@app_commands.describe(url='URL direto da imagem (ex: link do Discord, Imgur, etc.)')
async def setimagem(interaction: discord.Interaction, url: str):
    settings = load_settings()
    settings['panelImage'] = url
    save_settings(settings)
    embed = discord.Embed(
        title='✅ Imagem do Painel Definida',
        description='Cria um novo painel com `/setup` para aplicar a imagem.',
        color=0x00FF00,
    )
    embed.set_image(url=url)
    await interaction.response.send_message(embed=embed, ephemeral=True)


bot.run(config['token'])
