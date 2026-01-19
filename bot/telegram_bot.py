"""Telegram bot implementation."""

import asyncio
import logging
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from .api_client import AITagAPIClient
from .config import Config

logger = logging.getLogger(__name__)


class AITagSearchBot:
    """Telegram bot for searching AI artwork."""
    
    def __init__(self, config: Config):
        """Initialize the bot.
        
        Args:
            config: Bot configuration
        """
        self.config = config
        self.api_client = AITagAPIClient(
            base_url=config.base_url,
            timeout=config.api_timeout,
            proxy_url=config.proxy_url
        )
        
        # Build application with custom settings
        app_builder = Application.builder().token(config.telegram_bot_token)
        
        # Add proxy if configured
        if config.proxy_url:
            app_builder.proxy_url(config.proxy_url)
            logger.info(f"Using proxy: {config.proxy_url}")
        
        # Set connection and read timeouts
        app_builder.connect_timeout(config.connection_timeout)
        app_builder.read_timeout(config.read_timeout)
        
        self.app = app_builder.build()
        
        # Register handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register command and message handlers."""
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("search", self.search_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
        # Handle plain text messages as search queries
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.text_message))
        
        # Add error handler
        self.app.add_error_handler(self.error_handler)
        
        logger.info("All handlers registered successfully")
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors."""
        logger.error(f"Exception while handling an update: {context.error}", exc_info=context.error)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        logger.info(f"Received /start command from user {update.effective_user.id}")
        welcome_message = (
            "🎨 <b>AI绘画搜索机器人</b>\n\n"
            "欢迎使用AI绘画搜索机器人！\n\n"
            "📖 <b>使用方法：</b>\n"
            "• 发送 <code>/search 关键词</code> 搜索图片\n"
            "• 直接发送关键词也可以搜索\n"
            "• 例如：<code>/search wuwa</code> 或直接发送 <code>wuwa</code>\n\n"
            "💡 <b>提示：</b>\n"
            "• 支持中文和英文关键词\n"
            "• 可以使用分页按钮浏览更多结果\n\n"
            "🔗 数据来源：https://aitag.win/\n"
        )
        try:
            await update.message.reply_text(welcome_message, parse_mode="HTML")
            logger.info("Successfully sent welcome message")
        except Exception as e:
            logger.error(f"Error sending welcome message: {e}", exc_info=True)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_message = (
            "📖 <b>帮助信息</b>\n\n"
            "<b>可用命令：</b>\n"
            "/start - 显示欢迎信息\n"
            "/search &lt;关键词&gt; - 搜索AI绘画作品\n"
            "/help - 显示此帮助信息\n\n"
            "<b>使用示例：</b>\n"
            "• <code>/search genshin impact</code>\n"
            "• <code>/search 原神</code>\n"
            "• 直接发送 <code>wuwa</code>\n\n"
            "如有问题，请访问：https://aitag.win/\n"
        )
        await update.message.reply_text(help_message, parse_mode="HTML")
    
    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /search command."""
        if not context.args:
            await update.message.reply_text(
                "❌ 请提供搜索关键词\n\n"
                "用法：<code>/search 关键词</code>\n"
                "例如：<code>/search wuwa</code>",
                parse_mode="HTML"
            )
            return
        
        keyword = " ".join(context.args)
        await self._perform_search(update, keyword, page=1)
    
    async def text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle plain text messages as search queries."""
        keyword = update.message.text.strip()
        if keyword:
            await self._perform_search(update, keyword, page=1)
    
    async def _perform_search(
        self,
        update: Update,
        keyword: str,
        page: int = 1,
        message_id: Optional[int] = None
    ):
        """Perform search and send results.
        
        Args:
            update: Telegram update object
            keyword: Search keyword
            page: Page number (1-indexed)
            message_id: Message ID to edit (for pagination)
        """
        # Send "searching..." message
        if message_id is None:
            status_msg = await update.message.reply_text(f"🔍 正在搜索 <b>{keyword}</b>...", parse_mode="HTML")
        
        # Perform search
        results = await self.api_client.search_works(
            keyword=keyword,
            page=page,
            page_size=self.config.results_per_page
        )
        
        if results is None:
            error_msg = "❌ 搜索失败，请稍后重试"
            if message_id:
                await update.callback_query.edit_message_text(error_msg)
            else:
                await status_msg.edit_text(error_msg)
            return
        
        works = self.api_client.extract_works(results)
        total_count = self.api_client.get_total_count(results)
        
        if not works:
            no_results_msg = f"😕 没有找到关于 <b>{keyword}</b> 的结果"
            if message_id:
                await update.callback_query.edit_message_text(no_results_msg, parse_mode="HTML")
            else:
                await status_msg.edit_text(no_results_msg, parse_mode="HTML")
            return
        
        # Format results
        message = self._format_search_results(keyword, works, page, total_count)
        
        # Create pagination buttons
        keyboard = self._create_pagination_keyboard(keyword, page, total_count)
        
        # Send or edit message
        if message_id:
            await update.callback_query.edit_message_text(
                message,
                parse_mode="HTML",
                reply_markup=keyboard,
                disable_web_page_preview=False
            )
        else:
            await status_msg.edit_text(
                message,
                parse_mode="HTML",
                reply_markup=keyboard,
                disable_web_page_preview=False
            )
    
    def _format_search_results(
        self,
        keyword: str,
        works: list,
        page: int,
        total_count: int
    ) -> str:
        """Format search results as a message.
        
        Args:
            keyword: Search keyword
            works: List of work dictionaries
            page: Current page number
            total_count: Total count of results
            
        Returns:
            Formatted message string
        """
        message = f"🎨 <b>搜索结果：{keyword}</b>\n\n"
        message += f"找到 <b>{total_count}</b> 个相关作品\n"
        message += f"第 <b>{page}</b> 页\n\n"
        message += "─" * 30 + "\n\n"
        
        for i, work in enumerate(works, 1):
            # Extract work information (adjust based on actual API response)
            work_id = work.get("id") or work.get("work_id") or work.get("pid")
            title = work.get("title") or work.get("name") or "无标题"
            tags = work.get("tags", [])
            
            # Format tags
            if isinstance(tags, list):
                tags_str = ", ".join(tags[:5])  # Show first 5 tags
            else:
                tags_str = str(tags)
            
            # Build work entry
            work_url = self.api_client.get_work_url(work_id)
            message += f"{i}️⃣ <b>{title}</b>\n"
            if tags_str:
                message += f"🏷️ {tags_str}\n"
            message += f"🔗 <a href='{work_url}'>查看详情</a>\n\n"
        
        return message
    
    def _create_pagination_keyboard(
        self,
        keyword: str,
        current_page: int,
        total_count: int
    ) -> InlineKeyboardMarkup:
        """Create pagination keyboard.
        
        Args:
            keyword: Search keyword
            current_page: Current page number
            total_count: Total count of results
            
        Returns:
            InlineKeyboardMarkup with pagination buttons
        """
        total_pages = (total_count + self.config.results_per_page - 1) // self.config.results_per_page
        
        buttons = []
        
        # Previous page button
        if current_page > 1:
            buttons.append(
                InlineKeyboardButton(
                    "⬅️ 上一页",
                    callback_data=f"search:{keyword}:{current_page - 1}"
                )
            )
        
        # Page indicator
        buttons.append(
            InlineKeyboardButton(
                f"📄 {current_page}/{total_pages}",
                callback_data="noop"
            )
        )
        
        # Next page button
        if current_page < total_pages:
            buttons.append(
                InlineKeyboardButton(
                    "下一页 ➡️",
                    callback_data=f"search:{keyword}:{current_page + 1}"
                )
            )
        
        return InlineKeyboardMarkup([buttons])
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks for pagination."""
        query = update.callback_query
        await query.answer()
        
        # Parse callback data
        data = query.data
        
        if data == "noop":
            return
        
        if data.startswith("search:"):
            parts = data.split(":", 2)
            if len(parts) == 3:
                _, keyword, page_str = parts
                try:
                    page = int(page_str)
                    await self._perform_search(
                        update,
                        keyword,
                        page=page,
                        message_id=query.message.message_id
                    )
                except ValueError:
                    await query.edit_message_text("❌ 无效的页码")
    
    async def post_init(self, application: Application) -> None:
        """Called after the application is initialized."""
        bot_info = await application.bot.get_me()
        logger.info(f"Bot started successfully! Username: @{bot_info.username}")
        logger.info(f"Bot ID: {bot_info.id}")
        logger.info("Polling for updates...")
    
    async def post_shutdown(self, application: Application) -> None:
        """Called after the application shuts down."""
        logger.info("Bot stopped")
    
    async def _manual_polling(self):
        """Manual polling using httpx to call getUpdates directly."""
        import httpx
        
        base_url = f"https://api.telegram.org/bot{self.config.telegram_bot_token}"
        offset = 0
        
        # Configure proxy
        proxy_url = self.config.proxy_url
        
        logger.info(f"Starting manual polling with proxy: {proxy_url}")
        
        # Create client with or without proxy
        if proxy_url:
            # Create proxy object
            proxy = httpx.Proxy(url=proxy_url)
            mounts = {
                "http://": httpx.AsyncHTTPTransport(proxy=proxy),
                "https://": httpx.AsyncHTTPTransport(proxy=proxy),
            }
            client = httpx.AsyncClient(mounts=mounts, timeout=60.0)
        else:
            client = httpx.AsyncClient(timeout=60.0)
        
        async with client:
            while True:
                try:
                    # Call getUpdates
                    response = await client.post(
                        f"{base_url}/getUpdates",
                        json={
                            "offset": offset,
                            "timeout": 30,
                            "allowed_updates": ["message", "callback_query"]
                        }
                    )
                    
                    logger.debug(f"getUpdates response status: {response.status_code}")
                    
                    if response.status_code != 200:
                        logger.error(f"getUpdates failed with status {response.status_code}: {response.text}")
                        await asyncio.sleep(5)
                        continue
                    
                    data = response.json()
                    
                    if not data.get("ok"):
                        logger.error(f"getUpdates returned error: {data}")
                        await asyncio.sleep(5)
                        continue
                    
                    updates = data.get("result", [])
                    
                    if updates:
                        logger.info(f"Received {len(updates)} updates")
                    
                    for update_data in updates:
                        # Update offset
                        offset = update_data["update_id"] + 1
                        
                        try:
                            # Convert to Update object and process
                            update = Update.de_json(update_data, self.app.bot)
                            await self.app.process_update(update)
                        except Exception as e:
                            logger.error(f"Error processing update: {e}", exc_info=True)
                    
                except httpx.TimeoutException:
                    # Timeout is normal for long polling, just continue
                    logger.debug("getUpdates timeout, continuing...")
                    continue
                except httpx.RequestError as e:
                    logger.error(f"Request error in getUpdates: {e}", exc_info=True)
                    await asyncio.sleep(5)
                except Exception as e:
                    logger.error(f"Unexpected error in polling: {e}", exc_info=True)
                    await asyncio.sleep(5)
    
    def run(self):
        """Start the bot with manual polling."""
        import asyncio
        
        logger.info("Starting AI Tag Search Bot with manual polling...")
        
        async def start_bot():
            """Async function to start the bot."""
            try:
                # Initialize the application
                await self.app.initialize()
                logger.info("Application initialized")
                
                # Call post_init
                await self.post_init(self.app)
                
                # Start the application (but not the updater)
                await self.app.start()
                logger.info("Application started")
                
                # Delete webhook to ensure clean state
                await self.app.bot.delete_webhook(drop_pending_updates=True)
                logger.info("Webhook deleted, starting manual polling...")
                
                # Use manual polling instead of updater
                await self._manual_polling()
                    
            except KeyboardInterrupt:
                logger.info("Received shutdown signal")
            except Exception as e:
                logger.error(f"Error in bot: {e}", exc_info=True)
            finally:
                # Cleanup
                logger.info("Stopping bot...")
                await self.app.stop()
                await self.app.shutdown()
                await self.post_shutdown(self.app)
        
        # Run the async function
        try:
            asyncio.run(start_bot())
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            raise
