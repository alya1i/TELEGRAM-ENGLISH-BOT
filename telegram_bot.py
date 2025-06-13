import os
import json
import random
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler, CallbackQueryHandler

from helper import load_words, save_words, get_word_data

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

MENU, ADD_WORD, QUIZ, QUIZ_ANSWER, LIST_WORDS = range(5)

def start(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("📘 Add Word", callback_data="add_word")],
        [InlineKeyboardButton("📝 Quiz", callback_data="quiz")],
        [InlineKeyboardButton("📜 List Words", callback_data="list_words")],
        [InlineKeyboardButton("🌟 Word of the Day", callback_data="word_of_day")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "👋 Welcome to Alya English Learning Bot!\nChoose an option below to start learning:"
    
    if update.callback_query:
        query = update.callback_query
        query.answer()
        query.message.edit_text(text=text, reply_markup=reply_markup)
    else:
        update.message.reply_text(text=text, reply_markup=reply_markup)
    return MENU

def menu_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    choice = query.data

    if choice == "add_word":
        query.message.reply_text("🔤 Please send the English word you want to add:")
        return ADD_WORD
    elif choice == "quiz":
        return start_quiz(update, context)
    elif choice == "list_words":
        return list_words(update, context)
    elif choice == "word_of_day":
        return word_of_day(update, context)
    elif choice == "menu":
        return start(update, context)
    elif choice == "cancel":
        return cancel(update, context)
    else:
        query.message.reply_text("❓ Please choose a valid option.", reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔁 Back to Menu", callback_data="menu")
        ]]))
        return MENU

def add_word(update: Update, context: CallbackContext):
    word = update.message.text.strip().lower()
    if not word.isalpha():
        update.message.reply_text(
            "❌ Please enter a valid English word (letters only).",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔁 Back to Menu", callback_data="menu")
            ]])
        )
        return MENU

    update.message.reply_text("⏳ Fetching meaning, synonyms, and example...")
    data = get_word_data(word)
    if not data:
        update.message.reply_text(
            "❌ Couldn't find data for this word. Try another one!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔁 Back to Menu", callback_data="menu")
            ]])
        )
        return MENU

    words = load_words()
    words[word] = {
        "meaning": data["meaning"],
        "synonyms": data["synonyms"],
        "example": data["example"]
    }
    save_words(words)

    update.message.reply_text(
        f"✅ Word '{word}' saved!\n\n"
        f"📝 Arabic meaning: {data['meaning']}\n"
        f"🟰 Synonyms: {', '.join(data['synonyms']) or 'None'}\n"
        f"📖 Example: {data['example']}",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔁 Back to Menu", callback_data="menu"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel")
        ]])
    )
    return MENU

def list_words(update: Update, context: CallbackContext):
    words = load_words()
    if not words:
        update.callback_query.message.reply_text("❗ No words saved yet.")
        return MENU

    message = "📜 Your saved words:\n\n"
    for word, data in words.items():
        message += f"🔤 {word}\n📝 Arabic: {data['meaning']}\n🟰 Synonyms: {', '.join(data['synonyms']) or 'None'}\n📖 Example: {data['example']}\n\n"

    update.callback_query.message.reply_text(message, reply_markup=InlineKeyboardMarkup([[
        InlineKeyboardButton("🔁 Back to Menu", callback_data="menu")
    ]]))
    return MENU

def word_of_day(update: Update, context: CallbackContext):
    words = load_words()
    if not words:
        update.callback_query.message.reply_text("❗ No words saved yet.")
        return MENU

    word = random.choice(list(words.keys()))
    data = words[word]
    update.callback_query.message.reply_text(
        f"🌟 Word of the Day: {word}\n\n"
        f"📝 Arabic meaning: {data['meaning']}\n"
        f"🟰 Synonyms: {', '.join(data['synonyms']) or 'None'}\n"
        f"📖 Example: {data['example']}",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔁 Back to Menu", callback_data="menu")
        ]])
    )
    return MENU

def start_quiz(update: Update, context: CallbackContext):
    words = load_words()
    if len(words) < 4:
        update.callback_query.message.reply_text("❗ Need at least 4 words for a quiz.")
        return MENU

    all_words = list(words.keys())
    random.shuffle(all_words)
    quiz_questions = []
    for word in all_words[:5]:
        synonyms = words[word]['synonyms']
        if synonyms:
            options = [word]
            while len(options) < 4:
                random_word = random.choice(all_words)
                if random_word not in options:
                    options.append(random_word)
            random.shuffle(options)
            quiz_questions.append((word, random.choice(synonyms), options))

    if len(quiz_questions) < 3:
        update.callback_query.message.reply_text("❗ Not enough words with synonyms for quiz.")
        return MENU

    context.user_data['quiz_questions'] = quiz_questions
    context.user_data['quiz_index'] = 0
    context.user_data['score'] = 0
    return ask_next_question(update, context)

def ask_next_question(update: Update, context: CallbackContext):
    index = context.user_data['quiz_index']
    questions = context.user_data['quiz_questions']
    word, synonym, options = questions[index]
    context.user_data['current_answer'] = word

    keyboard = [[InlineKeyboardButton(opt, callback_data=opt) for opt in options]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.message.reply_text(
        f"❓ Question {index+1}/{len(questions)}:\nWhich word matches this synonym: {synonym}",
        reply_markup=reply_markup
    )
    return QUIZ_ANSWER

def check_quiz_answer(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user_answer = query.data
    correct_answer = context.user_data.get('current_answer')

    if user_answer == correct_answer:
        context.user_data['score'] += 1
        query.message.reply_text("✅ Correct!")
    else:
        query.message.reply_text(f"❌ Wrong. The correct word was: {correct_answer}")

    context.user_data['quiz_index'] += 1
    if context.user_data['quiz_index'] < len(context.user_data['quiz_questions']):
        return ask_next_question(update, context)
    else:
        score = context.user_data['score']
        query.message.reply_text(
            f"🎉 Quiz finished! Your score: {score}/{len(context.user_data['quiz_questions'])}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔁 Back to Menu", callback_data="menu")
            ]])
        )
        return MENU

def cancel(update: Update, context: CallbackContext):
    if update.callback_query:
        update.callback_query.message.reply_text("👋 Conversation ended. Type /start to begin again.")
    else:
        update.message.reply_text("👋 Conversation ended. Type /start to begin again.")
    return ConversationHandler.END

def error_handler(update: Update, context: CallbackContext):
    """Handle errors in the conversation."""
    print(f"Update {update} caused error {context.error}")
    if update.callback_query:
        update.callback_query.message.reply_text(
            "⚠️ An error occurred. Let's go back to the main menu.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔁 Back to Menu", callback_data="menu")
            ]])
        )
    elif update.message:
        update.message.reply_text(
            "⚠️ An error occurred. Let's go back to the main menu.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔁 Back to Menu", callback_data="menu")
            ]])
        )
    return MENU

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENU: [CallbackQueryHandler(menu_handler)],
            ADD_WORD: [MessageHandler(Filters.text & ~Filters.command, add_word)],
            QUIZ: [CallbackQueryHandler(start_quiz)],
            QUIZ_ANSWER: [CallbackQueryHandler(check_quiz_answer)],
            LIST_WORDS: [CallbackQueryHandler(list_words)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    dp.add_handler(conv_handler)
    dp.add_error_handler(error_handler)
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()