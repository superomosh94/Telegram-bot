import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import dialogflow_v2 as dialogflow
from google.api_core.exceptions import GoogleAPICallError, RetryError
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Dialogflow settings
DIALOGFLOW_PROJECT_ID = os.getenv('DIALOGFLOW_PROJECT_ID')
DIALOGFLOW_LANGUAGE_CODE = 'en'
SESSION_ID = 'current-user-id'  # In a real app, you'd use the user's Telegram ID

class AITelegramBot:
    def __init__(self, telegram_token):
        self.updater = Updater(telegram_token, use_context=True)
        self.dp = self.updater.dispatcher
        
        # Add handlers
        self.dp.add_handler(CommandHandler("start", self.start))
        self.dp.add_handler(CommandHandler("help", self.help))
        self.dp.add_handler(MessageHandler(Filters.text & ~Filters.command, self.handle_message))
        
        # Add error handler
        self.dp.add_error_handler(self.error_handler)

    def start(self, update: Update, context: CallbackContext) -> None:
        """Send a message when the command /start is issued."""
        user = update.effective_user
        update.message.reply_markdown_v2(
            fr'Hi {user.mention_markdown_v2()}\! I\'m an AI\-powered bot\. '
            'Ask me anything and I\'ll do my best to help\!'
        )

    def help(self, update: Update, context: CallbackContext) -> None:
        """Send a message when the command /help is issued."""
        help_text = """
        🤖 AI Bot Help:
        
        Just send me a message and I'll try to understand and respond!
        
        Commands:
        /start - Start interacting with the bot
        /help - Show this help message
        """
        update.message.reply_text(help_text)

    def detect_intent(self, text, user_id):
        """Detect the intent of the user's text using Dialogflow."""
        session_client = dialogflow.SessionsClient()
        session = session_client.session_path(DIALOGFLOW_PROJECT_ID, user_id)
        
        text_input = dialogflow.types.TextInput(
            text=text, language_code=DIALOGFLOW_LANGUAGE_CODE)
        query_input = dialogflow.types.QueryInput(text=text_input)
        
        try:
            response = session_client.detect_intent(
                session=session, query_input=query_input)
            return response.query_result
        except (GoogleAPICallError, RetryError) as e:
            logger.error(f"Dialogflow API error: {e}")
            return None

    def handle_message(self, update: Update, context: CallbackContext) -> None:
        """Handle incoming messages and respond using NLP."""
        user_id = str(update.effective_user.id)
        user_message = update.message.text
        
        logger.info(f"User {user_id} sent: {user_message}")
        
        # Get NLP response from Dialogflow
        try:
            result = self.detect_intent(user_message, user_id)
            
            if result is None:
                update.message.reply_text("I'm having trouble understanding. Please try again later.")
                return
                
            if result.intent.is_fallback:
                # Handle cases where the intent wasn't recognized
                update.message.reply_text("I'm not sure I understand. Can you rephrase that?")
            else:
                # Send the response from Dialogflow
                update.message.reply_text(result.fulfillment_text)
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            update.message.reply_text("Sorry, I encountered an error processing your message.")

    def error_handler(self, update: Update, context: CallbackContext) -> None:
        """Log errors and notify the user."""
        logger.error(msg="Exception while handling an update:", exc_info=context.error)
        
        if update and update.effective_message:
            update.effective_message.reply_text(
                "An error occurred while processing your request. "
                "The developers have been notified."
            )

    def run(self):
        """Start the bot."""
        self.updater.start_polling()
        logger.info("Bot is running...")
        self.updater.idle()

if __name__ == '__main__':
    # Load configuration
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    
    if not TELEGRAM_TOKEN or not DIALOGFLOW_PROJECT_ID:
        raise ValueError("Please set TELEGRAM_TOKEN and DIALOGFLOW_PROJECT_ID in environment variables")
    
    # Create and run bot
    bot = AITelegramBot(TELEGRAM_TOKEN)
    bot.run()