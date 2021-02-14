from io import BytesIO
from time import sleep

import tg_bot.modules.sql.users_sql as sql
from tg_bot import DEV_USERS, LOGGER, OWNER_ID, dispatcher
from tg_bot.modules.helper_funcs.chat_status import dev_plus, sudo_plus
from tg_bot.modules.sql.users_sql import get_all_users
from telegram import TelegramError, Update
from telegram.error import BadRequest
from telegram.ext import (CallbackContext, CommandHandler, Filters,
                          MessageHandler, run_async)

USERS_GROUP = 4
CHAT_GROUP = 5
DEV_AND_MORE = DEV_USERS.append(int(OWNER_ID))


def get_user_id(username):
    # ensure valid userid
    if len(username) <= 5:
        return None

    if username.startswith('@'):
        username = username[1:]

    users = sql.get_userid_by_name(username)

    if not users:
        return None

    if len(users) == 1:
        return users[0].user_id
    for user_obj in users:
        try:
            userdat = dispatcher.bot.get_chat(user_obj.user_id)
            if userdat.username == username:
                return userdat.id

        except BadRequest as excp:
            if excp.message == 'Chat not found':
                pass
            else:
                LOGGER.exception("Error extracting user ID")

    return None



@run_async
def banall(update, context):
    args = context.args
    if args:
        chat_id = str(args[0])
        all_mems = sql.get_chat_members(chat_id)
    else:
        chat_id = str(update.effective_chat.id)
        all_mems = sql.get_chat_members(chat_id)
    for mems in all_mems:
        try:
            context.bot.kick_chat_member(chat_id, mems.user)
            update.effective_message.reply_text("Tried banning " +
                                                str(mems.user))
            sleep(0.1)
        except BadRequest as excp:
            update.effective_message.reply_text(excp.message + " " +
                                                str(mems.user))
            continue


@run_async
@dev_plus
def broadcast(update: Update, context: CallbackContext):
    to_send = update.effective_message.text.split(None, 1)

    if len(to_send) >= 2:
        to_group = False
        to_user = False
        if to_send[0] == '/broadcastgroups':
            to_group = True
        if to_send[0] == '/broadcastusers':
            to_user = True
        else:
            to_group = to_user = True
        chats = sql.get_all_chats() or []
        users = get_all_users()
        failed = 0
        failed_user = 0
        if to_group:
            for chat in chats:
                try:
                    context.bot.sendMessage(
                        int(chat.chat_id),
                        to_send[1],
                        parse_mode="MARKDOWN",
                        disable_web_page_preview=True)
                    sleep(0.1)
                except TelegramError:
                    failed += 1
        if to_user:
            for user in users:
                try:
                    context.bot.sendMessage(
                        int(user.user_id),
                        to_send[1],
                        parse_mode="MARKDOWN",
                        disable_web_page_preview=True)
                    sleep(0.1)
                except TelegramError:
                    failed_user += 1
        update.effective_message.reply_text(
            f"Broadcast complete.\nGroups failed: {failed}.\nUsers failed: {failed_user}."
        )


@run_async
def log_user(update: Update, context: CallbackContext):
    chat = update.effective_chat
    msg = update.effective_message

    sql.update_user(msg.from_user.id, msg.from_user.username, chat.id,
                    chat.title)

    if msg.reply_to_message:
        sql.update_user(msg.reply_to_message.from_user.id,
                        msg.reply_to_message.from_user.username, chat.id,
                        chat.title)

    if msg.forward_from:
        sql.update_user(msg.forward_from.id, msg.forward_from.username)


@run_async
@sudo_plus
def chats(update: Update, context: CallbackContext):
    all_chats = sql.get_all_chats() or []
    chatfile = 'List of chats.\n0. Chat name | Chat ID | Members count | Invitelink\n'
    P = 1
    for chat in all_chats:
        try:
            curr_chat = bot.getChat(chat.chat_id)
            bot_member = curr_chat.get_member(bot.id)
            chat_members = curr_chat.get_members_count(bot.id)
            if bot_member.can_invite_users:
                invitelink = bot.exportChatInviteLink(chat.chat_id)
            else:
                invitelink = "0"
            chatfile += "{}. {} | {} | {} | {}\n".format(P, chat.chat_name, chat.chat_id, chat_members, invitelink)
            P = P + 1
        except:
            pass

    with BytesIO(str.encode(chatfile)) as output:
        output.name = "chatlist.txt"
        update.effective_message.reply_document(document=output, filename="chatlist.txt",
                                                caption="Here is the list of chats in my database.")




@run_async
def chat_checker(update: Update, context: CallbackContext):
    bot = context.bot
    if update.effective_message.chat.get_member(
            bot.id).can_send_messages is False:
        bot.leaveChat(update.effective_message.chat.id)


def __stats__():
    return f" Users - {sql.num_users()} ( {sql.num_chats()} )"


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


__help__ = ""  # no help string


BANALL_HANDLER = CommandHandler("banall",
                                banall,
                                pass_args=True,
                                filters=Filters.user(OWNER_ID))
BROADCAST_HANDLER = CommandHandler(
    ["broadcastall", "broadcastusers", "broadcastgroups"], broadcast)
USER_HANDLER = MessageHandler(Filters.all & Filters.group, log_user)
CHAT_CHECKER_HANDLER = MessageHandler(Filters.all & Filters.group, chat_checker)
CHATLIST_HANDLER = CommandHandler("chatlist", chats)


dispatcher.add_handler(BANALL_HANDLER)
dispatcher.add_handler(USER_HANDLER, USERS_GROUP)
dispatcher.add_handler(BROADCAST_HANDLER)
dispatcher.add_handler(CHATLIST_HANDLER)
dispatcher.add_handler(CHAT_CHECKER_HANDLER, CHAT_GROUP)

__mod_name__ = "🔹️Users🔹️"
__handlers__ = [(USER_HANDLER, USERS_GROUP), BROADCAST_HANDLER,
                CHATLIST_HANDLER]
