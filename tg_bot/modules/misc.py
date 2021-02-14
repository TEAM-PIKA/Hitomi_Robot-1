import requests
import random, re
import wikipedia
from typing import Optional, List
from requests import get


from datetime import datetime
from io import BytesIO
from tswift import Song
from bs4 import BeautifulSoup

from telegram import (Chat, ParseMode, ChatAction, TelegramError, Update,
                      InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove)

from telegram.ext import CallbackContext ,CommandHandler, run_async, Filters
from telegram.utils.helpers import escape_markdown
from telegram.error import BadRequest

from tg_bot import (OWNER_ID, SUDO_USERS, SUPPORT_USERS, WHITELIST_USERS, DEV_USERS,
                           dispatcher)
from tg_bot.__main__ import STATS, GDPR
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.filters import CustomFilters
from tg_bot.modules.helper_funcs.alternate import typing_action , send_action


@run_async
def gifid(update: Update, context: CallbackContext):
    msg = update.effective_message
    if msg.reply_to_message and msg.reply_to_message.animation:
        update.effective_message.reply_text(
            f"Gif ID:\n<code>{msg.reply_to_message.animation.file_id}</code>",
            parse_mode=ParseMode.HTML)
    else:
        update.effective_message.reply_text(
            "Please reply to a gif to get its ID.")


@run_async
def paste(update: Update, context: CallbackContext):
    args = context.args
    message = update.effective_message

    if message.reply_to_message:
        data = message.reply_to_message.text

    elif len(args) >= 1:
        data = message.text.split(None, 1)[1]

    else:
        message.reply_text("What am I supposed to do with this?")
        return

    key = (
        requests.post("https://nekobin.com/api/documents", json={"content": data})
        .json()
        .get("result")
        .get("key")
    )

    url = f"https://nekobin.com/{key}"

    reply_text = f"Nekofied to *Nekobin* : {url}"

    message.reply_text(
        reply_text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True
    )

@run_async
@typing_action
def lyrics(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    msg = update.effective_message
    query = " ".join(args)
    song = ""
    if not query:
        msg.reply_text("You haven't specified which song to look for!")
        return
    song = Song.find_song(query)
    if song:
        if song.lyrics:
            reply = song.format()
        else:
            reply = "Couldn't find any lyrics for that song!"
    else:
        reply = "Song not found!"
    if len(reply) > 4090:
        with open("lyrics.txt", 'w') as f:
            f.write(f"{reply}\n\n\nOwO UwU OmO")
        with open("lyrics.txt", 'rb') as f:
            msg.reply_document(document=f,
            caption="Message length exceeded max limit! Sending as a text file.")
    else:
        msg.reply_text(reply)


@run_async
@typing_action
def github(update, context):
    message = update.effective_message
    text = message.text[len('/git '):]
    usr = get(f'https://api.github.com/users/{text}').json()
    if usr.get('login'):
        text = f"*Username:* [{usr['login']}](https://github.com/{usr['login']})"

        whitelist = [
            'name', 'id', 'type', 'location', 'blog', 'bio', 'followers',
            'following', 'hireable', 'public_gists', 'public_repos', 'email',
            'company', 'updated_at', 'created_at'
        ]

        difnames = {
            'id': 'Account ID',
            'type': 'Account type',
            'created_at': 'Account created at',
            'updated_at': 'Last updated',
            'public_repos': 'Public Repos',
            'public_gists': 'Public Gists'
        }

        goaway = [None, 0, 'null', '']

        for x, y in usr.items():
            if x in whitelist:
                if x in difnames:
                    x = difnames[x]
                else:
                    x = x.title()

                if x == 'Account created at' or x == 'Last updated':
                    y = datetime.strptime(y, "%Y-%m-%dT%H:%M:%SZ")

                if y not in goaway:
                    if x == 'Blog':
                        x = "Website"
                        y = f"[Here!]({y})"
                        text += ("\n*{}:* {}".format(x, y))
                    else:
                        text += ("\n*{}:* `{}`".format(x, y))
        reply_text = text
    else:
        reply_text = "User not found. Make sure you entered valid username!"
    message.reply_text(reply_text,
                       parse_mode=ParseMode.MARKDOWN,
                       disable_web_page_preview=True)


@run_async
def repo(update, context):
    args = context.args
    message = update.effective_message
    text = message.text[len('/repo '):]
    usr = get(f'https://api.github.com/users/{text}/repos?per_page=40').json()
    reply_text = "*Repositorys*\n"
    for i in range(len(usr)):
        reply_text += f"[{usr[i]['name']}]({usr[i]['html_url']})\n"
    message.reply_text(reply_text,
                       parse_mode=ParseMode.MARKDOWN,
                       disable_web_page_preview=True)



@run_async
@typing_action
def mpaste(update, context):
    args = context.args 
    BURL = 'https://del.dog'
    message = update.effective_message
    if message.reply_to_message:
        data = message.reply_to_message.text
    elif len(args) >= 1:
        data = message.text.split(None, 1)[1]
    else:
        message.reply_text("What am I supposed to do with this?!")
        return

    r = requests.post(f'{BURL}/documents', data=data.encode('utf-8'))

    if r.status_code == 404:
        update.effective_message.reply_text("Failed to reach dogbin")
        r.raise_for_status()

    res = r.json()

    if r.status_code != 200:
        update.effective_message.reply_text(res['message'])
        r.raise_for_status()

    key = res['key']
    if res['isUrl']:
        reply = "Shortened URL: {}/{}\nYou can view stats, etc. [here]({}/v/{})".format(BURL, key, BURL, key)
    else:
        reply = f'{BURL}/{key}'
    update.effective_message.reply_text(reply,
                                        parse_mode=ParseMode.MARKDOWN,
                                        disable_web_page_preview=True)


@run_async
@typing_action
def get_paste_content(update, context):
    args = context.args
    BURL = 'https://del.dog'
    message = update.effective_message
    chat = update.effective_chat  # type: Optional[Chat]

    if len(args) >= 1:
        key = args[0]
    else:
        message.reply_text("Please supply a dogbin url!")
        return

    format_normal = f'{BURL}/'
    format_view = f'{BURL}/v/'

    if key.startswith(format_view):
        key = key[len(format_view):]
    elif key.startswith(format_normal):
        key = key[len(format_normal):]

    r = requests.get(f'{BURL}/raw/{key}')

    if r.status_code != 200:
        try:
            res = r.json()
            update.effective_message.reply_text(res['message'])
        except Exception:
            if r.status_code == 404:
                update.effective_message.reply_text(
                    "Failed to reach dogbin")
            else:
                update.effective_message.reply_text(
                    "Unknown error occured")
        r.raise_for_status()

    update.effective_message.reply_text('```' + escape_markdown(r.text) +
                                        '```',
                                        parse_mode=ParseMode.MARKDOWN)


@run_async
@typing_action
def echo(update, context):
    args = update.effective_message.text.split(None, 1)
    message = update.effective_message
    if message.reply_to_message:
        message.reply_to_message.reply_text(args[1])
    else:
        message.reply_text(args[1], quote=False)
    try:
        message.delete()
    except:
        pass  


@run_async
@typing_action
def gdpr(update, context):
    update.effective_message.reply_text("Deleting identifiable data...")
    for mod in GDPR:
        mod.__gdpr__(update.effective_user.id)

    update.effective_message.reply_text(
        "Your personal data has been deleted.\n\nNote that this will not unban "
        f"you from any chats, as that is telegram data, not {dispatcher.bot.first_name} data. "
        "Flooding, warns, and gbans are also preserved, as of "
        "[this](https://ico.org.uk/for-organisations/guide-to-the-general-data-protection-regulation-gdpr/individual-rights/right-to-erasure/), "
        "which clearly states that the right to erasure does not apply "
        '"for the performance of a task carried out in the public interest", as is '
        "the case for the aforementioned pieces of data.",
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )


MARKDOWN_HELP = """
Markdown is a very powerful formatting tool supported by telegram. {} has some enhancements, to make sure that \
saved messages are correctly parsed, and to allow you to create buttons.

- <code>_italic_</code>: wrapping text with '_' will produce italic text
- <code>*bold*</code>: wrapping text with '*' will produce bold text
- <code>`code`</code>: wrapping text with '`' will produce monospaced text, also known as 'code'
- <code>~strike~</code> wrapping text with '~' will produce strikethrough text
- <code>--underline--</code> wrapping text with '--' will produce underline text
- <code>[sometext](someURL)</code>: this will create a link - the message will just show <code>sometext</code>, \
and tapping on it will open the page at <code>someURL</code>.
EG: <code>[test](example.com)</code>

- <code>[buttontext](buttonurl:someURL)</code>: this is a special enhancement to allow users to have telegram \
buttons in their markdown. <code>buttontext</code> will be what is displayed on the button, and <code>someurl</code> \
will be the url which is opened.
EG: <code>[This is a button](buttonurl:example.com)</code>

If you want multiple buttons on the same line, use :same, as such:
<code>[one](buttonurl://example.com)
[two](buttonurl://google.com:same)</code>
This will create two buttons on a single line, instead of one button per line.

Keep in mind that your message <b>MUST</b> contain some text other than just a button!
""".format(
    dispatcher.bot.first_name
)



@run_async
@typing_action
def markdown_help(update, context):
    update.effective_message.reply_text(MARKDOWN_HELP, parse_mode=ParseMode.HTML)
    update.effective_message.reply_text(
        "Try forwarding the following message to me, and you'll see!"
    )
    update.effective_message.reply_text(
        "/save test This is a markdown test. _italics_, --underline--, *bold*, `code`, ~strike~ "
        "[URL](example.com) [button](buttonurl:github.com) "
        "[button2](buttonurl://google.com:same)"
    )


@run_async
@typing_action
def wiki(update, context):
    kueri = re.split(pattern="wiki", string=update.effective_message.text)
    wikipedia.set_lang("en")
    if len(str(kueri[1])) == 0:
        update.effective_message.reply_text("Enter keywords!")
    else:
        try:
            pertama = update.effective_message.reply_text("🔄 Loading...")
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="🔧 More Info...", url=wikipedia.page(kueri).url
                        )
                    ]
                ]
            )
            context.bot.editMessageText(
                chat_id=update.effective_chat.id,
                message_id=pertama.message_id,
                text=wikipedia.summary(kueri, sentences=10),
                reply_markup=keyboard,
            )
        except wikipedia.PageError as e:
            update.effective_message.reply_text(f"⚠ Error: {e}")
        except BadRequest as et:
            update.effective_message.reply_text(f"⚠ Error: {et}")
        except wikipedia.exceptions.DisambiguationError as eet:
            update.effective_message.reply_text(
                f"⚠ Error\n There are too many query! Express it more!\nPossible query result:\n{eet}"
            )


@run_async
@typing_action
def ud(update, context):
    msg = update.effective_message
    args = context.args
    text = " ".join(args).lower()
    if not text:
        msg.reply_text("Please enter keywords to search!")
        return
    try:
        results = get(f"http://api.urbandictionary.com/v0/define?term={text}").json()
        reply_text = f'Word: {text}\nDefinition: {results["list"][0]["definition"]}'
        reply_text += f'\n\nExample: {results["list"][0]["example"]}'
    except IndexError:
        reply_text = (
            f"Word: {text}\nResults: Sorry could not find any matching results!"
        )
    ignore_chars = "[]"
    reply = reply_text
    for chars in ignore_chars:
        reply = reply.replace(chars, "")
    if len(reply) >= 4096:
        reply = reply[:4096]  # max msg lenth of tg.
    try:
        msg.reply_text(reply)
    except BadRequest as err:
        msg.reply_text(f"Error! {err.message}")


@run_async
@typing_action
def getlink(update, context):
    args = context.args
    message = update.effective_message
    if args:
        pattern = re.compile(r"-\d+")
    else:
        message.reply_text("You don't seem to be referring to any chats.")
    links = "Invite link(s):\n"
    for chat_id in pattern.findall(message.text):
        try:
            chat = context.bot.getChat(chat_id)
            bot_member = chat.get_member(context.bot.id)
            if bot_member.can_invite_users:
                invitelink = context.bot.exportChatInviteLink(chat_id)
                links += str(chat_id) + ":\n" + invitelink + "\n"
            else:
                links += (
                    str(chat_id) + ":\nI don't have access to the invite link." + "\n"
                )
        except BadRequest as excp:
            links += str(chat_id) + ":\n" + excp.message + "\n"
        except TelegramError as excp:
            links += str(chat_id) + ":\n" + excp.message + "\n"

    message.reply_text(links)




@run_async
@typing_action
def app(update: Update, _):
    message = update.effective_message
    try:
        progress_message = update.effective_message.reply_text(
            "Searching In Play-Store.... ")
        app_name = message.text[len('/app '):]
        remove_space = app_name.split(' ')
        final_name = '+'.join(remove_space)
        page = requests.get(
            f"https://play.google.com/store/search?q={final_name}&c=apps")
        soup = BeautifulSoup(page.content, 'lxml', from_encoding='utf-8')
        results = soup.findAll("div", "ZmHEEd")
        app_name = results[0].findNext(
            'div', 'Vpfmgd').findNext(
            'div', 'WsMG1c nnK0zc').text
        app_dev = results[0].findNext(
            'div', 'Vpfmgd').findNext(
            'div', 'KoLSrc').text
        app_dev_link = "https://play.google.com" + results[0].findNext(
            'div', 'Vpfmgd').findNext('a', 'mnKHRc')['href']
        app_rating = results[0].findNext('div', 'Vpfmgd').findNext(
            'div', 'pf5lIe').find('div')['aria-label']
        app_link = "https://play.google.com" + results[0].findNext(
            'div', 'Vpfmgd').findNext('div', 'vU6FJ p63iDd').a['href']
        app_icon = results[0].findNext(
            'div', 'Vpfmgd').findNext(
            'div', 'uzcko').img['data-src']
        app_details = "<a href='" + app_icon + "'>📲&#8203;</a>"
        app_details += " <b>" + app_name + "</b>"
        app_details += "\n\n<i>Developer :</i> <a href='" + app_dev_link + "'>"
        app_details += app_dev + "</a>"
        app_details += "\n<i>Rating :</i> " + app_rating.replace(
            "Rated ", "⭐️ ").replace(" out of ", "/").replace(
                " stars", "", 1).replace(" stars", "⭐️").replace("five", "5")
        app_details += "\n<i>Features :</i> <a href='" + \
            app_link + "'>View in Play Store</a>"
        message.reply_text(
            app_details,
            disable_web_page_preview=False,
            parse_mode='html')
    except IndexError:
        message.reply_text(
            "No Result Found In Search. Please Enter **Valid App Name**")
    except Exception as err:
        message.reply_text(err)
    progress_message.delete()




@run_async
@send_action(ChatAction.UPLOAD_PHOTO)
def rmemes(update, context):
    msg = update.effective_message
    chat = update.effective_chat

    SUBREDS = [
        "meirl",
        "dankmemes",
        "AdviceAnimals",
        "memes",
        "meme",
        "memes_of_the_dank",
        "PornhubComments",
        "teenagers",
        "memesIRL",
        "insanepeoplefacebook",
        "terriblefacebookmemes",
    ]

    subreddit = random.choice(SUBREDS)
    res = r.get(f"https://meme-api.herokuapp.com/gimme/{subreddit}")

    if res.status_code != 200:  # Like if api is down?
        msg.reply_text("Sorry some error occurred :(")
        return
    res = res.json()

    rpage = res.get(str("subreddit"))  # Subreddit
    title = res.get(str("title"))  # Post title
    memeu = res.get(str("url"))  # meme pic url
    plink = res.get(str("postLink"))

    caps = f"- <b>Title</b>: {title}\n"
    caps += f"- <b>Subreddit:</b> <pre>r/{rpage}</pre>"

    keyb = [[InlineKeyboardButton(text="Subreddit Postlink 🔗", url=plink)]]
    try:
        context.bot.send_photo(
            chat.id,
            photo=memeu,
            caption=(caps),
            reply_markup=InlineKeyboardMarkup(keyb),
            timeout=60,
            parse_mode=ParseMode.HTML,
        )

    except BadRequest as excp:
        return msg.reply_text(f"Error! {excp.message}")


@run_async
def slist(update, context):
    sfile = "List Of All Staff Users:"
    sfile += f"\n• DEV USER IDs :-  {DEV_USERS}"
    sfile += f"\n• SUDO USER IDs :- {SUDO_USERS}"
    sfile += f"\n• SUPPORT USER IDs :- {SUPPORT_USERS}"
    sfile += f"\n• WHITELIST USER IDs :- {WHITELIST_USERS}" 
    with BytesIO(str.encode(sfile)) as output:
        output.name = "staff-ids.txt"
        update.effective_message.reply_document(
            document=output,
            filename="staff-ids.txt",
            caption="Here is the list of all staff users.",
        )


@run_async
def reply_keyboard_remove(update, context):
    reply_keyboard = []
    reply_keyboard.append([ReplyKeyboardRemove(remove_keyboard=True)])
    reply_markup = ReplyKeyboardRemove(remove_keyboard=True)
    old_message = context.bot.send_message(
        chat_id=update.message.chat_id,
        text='Trying',  
        reply_markup=reply_markup,
        reply_to_message_id=update.message.message_id)
    context.bot.delete_message(chat_id=update.message.chat_id,
                       message_id=old_message.message_id)



@run_async
def stats(update, context):
    stats = f"┎─⌈ <b>Current {dispatcher.bot.first_name} Stats</b> ⌋\n┇\n" + "\n┋\n".join([mod.__stats__() for mod in STATS])
    result = re.sub(r'(\d+)', r'<code>\1</code>', stats)
    update.effective_message.reply_text(result, parse_mode=ParseMode.HTML)




# /ip is for private use
__help__ = """
*Info:*
 - /info: Get information about a user.
 - /id: Get the current group id. If used by replying to a message, gets that user's id.
 - /whois : Get information about user using pyrogram  method
 - /dinfo: Get info about user with more data 
 - /spbinfo: get information about in spam protection bot 

*Animations:*
 - /love : - love animation
 - /hack : - hack animation
 - /moon : - moon animation
 - /block : - block animation
 - /earth : - earth animation
 - /clock : - clock animation
 - /bombs : - bombs animation
 - /kill : - kill animation
 - /dice : - dice animation
 - /basket : - basketball animation 
 - /dice : - dice animation

*Translator:*
 - /tr or /tl: - To translate to your language, by default language is set to english, use `/tr <lang code>` for some other language!
 - /splcheck: - As a reply to get grammar corrected text of gibberish message.
 - /tts: - To some message to convert it into audio format!
 - /stt :- convert audio to text ( only English)

*Use in bot pm:* ( admin can use in group)
 - /google <text> :- search google queries
 - /images  <text> : search images 

*Github:*
 - /git: Returns info about a GitHub user or organization.
 - /repo: Return the GitHub user or organization repository list (Limited at 40) 

*Covid:*
 - /covid :To get Global data	
 - /covid <country>:To get data of a country

*Qrcode:*
 - /getqr: get the qr code content from the replied qr code
 - /makeqr <content>: make a qr code from the given message (text, link, etc...)

*More:*
 - /deepfry : reply to img deepfry it
 - /q : make quote of massage
 - /paste: Create a paste or a shortened url using nekobin
 - /getpaste: Get the content of a paste or shortened url from [dogbin](https://del.dog)
 - /wiki : Search wikipedia articles.
 - /ud <query> : Search stuffs in urban dictionary.
 - /wall <query> : Get random wallpapers directly from bot! 
 - /weather <city>: Gets weather information of particular place!
 - /reverse : Reverse searches image or stickers on google.
 - /gdpr: Deletes your information from the bot's database. Private chats only.
 - /markdownhelp: Quick summary of how markdown works in telegram - can only be called in private chats.
 - /removebotkeyboard: Got a nasty bot keyboard stuck in your group?
 - /app <app name>: Finds an app in playstore for you
 - /cash: currency converter
 - /time <query>: Gives information about a timezone.
 - /plet <text> : make ur text sticker in different colours

\
"""

__mod_name__ = "🔹️Extras🔹️"

APP_HANDLER = DisableAbleCommandHandler("app", app)
LYRICS_HANDLER = DisableAbleCommandHandler("lyrics", lyrics, pass_args=True)
GIFID_HANDLER = DisableAbleCommandHandler("gifid", gifid) 
ECHO_HANDLER = CommandHandler("echo", echo, filters=CustomFilters.sudo_filter)
MD_HELP_HANDLER = CommandHandler("markdownhelp", markdown_help, filters=Filters.private)
STATS_HANDLER = DisableAbleCommandHandler("stats", stats, filters=CustomFilters.sudo_filter)
GDPR_HANDLER = CommandHandler("gdpr", gdpr, filters=Filters.private)
WIKI_HANDLER = DisableAbleCommandHandler("wiki", wiki)
UD_HANDLER = DisableAbleCommandHandler("ud", ud)
GETLINK_HANDLER = CommandHandler(
    "getlink", getlink, pass_args=True, filters=Filters.user(OWNER_ID)
)
STAFFLIST_HANDLER = CommandHandler(
    "slist", slist, filters=Filters.user(OWNER_ID)
)
REDDIT_MEMES_HANDLER = DisableAbleCommandHandler("rmeme", rmemes) 

GITHUB_HANDLER = DisableAbleCommandHandler("git", github, admin_ok=True)
REPO_HANDLER = DisableAbleCommandHandler("repo",
                                         repo,
                                         pass_args=True,
                                         admin_ok=True)


MPASTE_HANDLER = DisableAbleCommandHandler("mpaste", mpaste, pass_args=True)
PASTE_HANDLER = DisableAbleCommandHandler("paste", paste, pass_args=True)
GET_PASTE_HANDLER = DisableAbleCommandHandler("getpaste",
                                              get_paste_content,
                                              pass_args=True)



dispatcher.add_handler(APP_HANDLER)
dispatcher.add_handler(LYRICS_HANDLER)
dispatcher.add_handler(GITHUB_HANDLER)
dispatcher.add_handler(REPO_HANDLER)
dispatcher.add_handler(PASTE_HANDLER)
dispatcher.add_handler(MPASTE_HANDLER)
dispatcher.add_handler(GET_PASTE_HANDLER)
dispatcher.add_handler(UD_HANDLER)
dispatcher.add_handler(ECHO_HANDLER)
dispatcher.add_handler(MD_HELP_HANDLER)
dispatcher.add_handler(STATS_HANDLER)
dispatcher.add_handler(GDPR_HANDLER)
dispatcher.add_handler(WIKI_HANDLER)
dispatcher.add_handler(GETLINK_HANDLER)
dispatcher.add_handler(STAFFLIST_HANDLER)
dispatcher.add_handler(REDDIT_MEMES_HANDLER)
dispatcher.add_handler(GIFID_HANDLER)

dispatcher.add_handler(DisableAbleCommandHandler("removebotkeyboard", reply_keyboard_remove))


