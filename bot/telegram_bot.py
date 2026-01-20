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
        self.app.add_handler(CommandHandler("hot", self.hot_command))
        self.app.add_handler(CommandHandler("random", self.random_command))
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
            "🎨 <b>AI绘画搜索机器人 (aitag.win)</b>\n\n"
            "欢迎使用！这是一个功能强大的 AI 绘画作品搜索与咒语提取助手。\n\n"
            "🛠 <b>核心指令：</b>\n"
            "• 🔍 <code>/search 关键词</code> - 搜索特定题材的作品\n"
            "• 🔥 <code>/hot</code> - 查看本月全站热门排行榜\n"
            "• 🎲 <code>/random</code> - 抽个盲盒！随机看一张大作\n"
            "• 💡 <b>直接发送：</b>不需要指令，直接发关键词也能搜\n\n"
            "🌟 <b>进阶黑科技：</b>\n"
            "• 🏹 <code>/random 关键词</code> - 随机看特定主题的作品\n"
            "• 🏷 <b>标签跳转</b> - 点击详情页的标签按钮可直接开启新搜索\n"
            "• 📋 <b>一键复制</b> - 详情页支持一键生成可点击复制的完整提示词 (Prompt)\n\n"
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
            "📖 <b>全功能帮助菜单</b>\n\n"
            "<b>1️⃣ 基础搜索：</b>\n"
            "• <code>wuwa</code> - 直接发送词条即刻搜索\n"
            "• <code>/search 原神</code> - 使用命令搜索\n\n"
            "<b>2️⃣ 流行与发现：</b>\n"
            "• <code>/hot</code> - 本月最热门的作品排行\n"
            "• <code>/random</code> - 全站随机推荐一张美图\n"
            "• <code>/random 白髪</code> - <b>(新)</b> 随机推荐一张特定主题作品\n\n"
            "<b>3️⃣ 详情与咒语：</b>\n"
            "• <b>[数字按钮]</b> - 获取全量高清大图及生成参数\n"
            "• <b>[📋 复制咒语]</b> - 获取专为手机优化的可点击复制提示词\n"
            "• <b>[#标签按钮]</b> - 点击作品下方的标签实现连续跳转浏览\n\n"
            "<b>4️⃣ 其他：</b>\n"
            "• <code>/start</code> - 重显欢迎信息\n"
            "• <code>/help</code> - 打开此帮助菜单\n\n"
            "如有疑问或建议，请访问：https://aitag.win/\n"
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
    
    async def hot_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /hot command to show monthly ranking."""
        await self._show_ranking(update, page=1)
    
    async def random_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /random command with optional keyword."""
        keyword = " ".join(context.args) if context.args else None
        
        status_text = "🎲 正在抽取一张随机作品..."
        if keyword:
            status_text = f"🎲 正在抽取一张关于 <b>{keyword}</b> 的随机作品..."
            
        status_msg = await update.message.reply_text(status_text, parse_mode="HTML")
        work = await self.api_client.get_random_work(keyword)
        
        if not work:
            fail_text = "❌ 抽取失败，可能没有找到相关作品" if keyword else "❌ 抽取失败，请重试"
            await status_msg.edit_text(fail_text)
            return
            
        work_id = work.get("id") or work.get("work_id") or work.get("pid")
        await status_msg.delete()
        await self._send_work_detail(update, str(work_id), is_random=True)
    
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
            page_size=max(60, self.config.results_per_page)
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
        
        # Create pagination keyboard
        keyboard = self._create_pagination_keyboard(keyword, works, page, total_count)
        
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
    
    async def _show_ranking(
        self,
        update: Update,
        page: int = 1,
        message_id: Optional[int] = None
    ):
        """Show monthly ranking.
        
        Args:
            update: Telegram update object
            page: Page number (1-indexed)
            message_id: Message ID to edit (for pagination)
        """
        # Send "loading..." message
        if message_id is None:
            status_msg = await update.message.reply_text("🔥 正在获取本月热门排行榜...", parse_mode="HTML")
        
        # Fetch ranking
        results = await self.api_client.get_monthly_ranking(
            page=page,
            page_size=max(60, self.config.results_per_page)
        )
        
        if results is None:
            error_msg = "❌ 获取排行榜失败，请稍后重试"
            if message_id:
                await update.callback_query.edit_message_text(error_msg)
            else:
                await status_msg.edit_text(error_msg)
            return
        
        works = self.api_client.extract_works(results)
        total_count = self.api_client.get_total_count(results)
        
        if not works:
            no_results_msg = "😕 暂无排行榜数据"
            if message_id:
                await update.callback_query.edit_message_text(no_results_msg, parse_mode="HTML")
            else:
                await status_msg.edit_text(no_results_msg, parse_mode="HTML")
            return
        
        # Format results
        message = self._format_ranking_results(works, page, total_count)
        
        # Create pagination buttons
        keyboard = self._create_ranking_keyboard(works, page, total_count)
        
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
        
        Returns:
            Formatted message string
        """
        message = f"🔍 <b>搜索：{keyword}</b>\n"
        message += f"找到 <b>{total_count}</b> 个作品 | 第 <b>{page}</b> 页\n"
        message += "─" * 20 + "\n"
        
        display_works = works[:10]
        
        for i, work in enumerate(display_works, 1):
            title = work.get("title") or work.get("name") or "无标题"
            # Use a more compact format
            message += f"{i}. <b>{title}</b>\n"
        
        message += "\n💡 点击下方数字查看图片及提示词"
        return message
    
    def _format_ranking_results(
        self,
        works: list,
        page: int,
        total_count: int
    ) -> str:
        """Format ranking results as a message.
        
        Returns:
            Formatted message string
        """
        message = f"🔥 <b>本月热门排行榜</b>\n"
        message += f"共 <b>{total_count}</b> 个作品 | 第 <b>{page}</b> 页\n"
        message += "─" * 20 + "\n"
        
        display_works = works[:10]
        
        for i, work in enumerate(display_works, 1):
            title = work.get("title") or work.get("name") or "无标题"
            # Add ranking emoji for top 3
            rank_emoji = ""
            if page == 1:
                if i == 1:
                    rank_emoji = "🥇 "
                elif i == 2:
                    rank_emoji = "🥈 "
                elif i == 3:
                    rank_emoji = "🥉 "
            
            message += f"{rank_emoji}{i}. <b>{title}</b>\n"
        
        message += "\n💡 点击下方数字查看图片及提示词"
        return message
    
    def _create_ranking_keyboard(
        self,
        works: list,
        current_page: int,
        total_count: int
    ) -> InlineKeyboardMarkup:
        """Create keyboard for ranking with detail buttons and pagination."""
        total_pages = (total_count + self.config.results_per_page - 1) // self.config.results_per_page
        
        keyboard = []
        
        # Detail buttons in rows of 5
        display_works = works[:10]
        detail_rows = []
        for i, work in enumerate(display_works, 1):
            work_id = work.get("id") or work.get("work_id") or work.get("pid")
            detail_rows.append(InlineKeyboardButton(str(i), callback_data=f"detail:{work_id}"))
            if len(detail_rows) == 5:
                keyboard.append(detail_rows)
                detail_rows = []
        if detail_rows:
            keyboard.append(detail_rows)
            
        # Pagination row
        nav_buttons = []
        if current_page > 1:
            nav_buttons.append(InlineKeyboardButton("⬅️ 上一页", callback_data=f"rank:{current_page - 1}"))
        
        nav_buttons.append(InlineKeyboardButton(f"📄 {current_page}/{total_pages}", callback_data="noop"))
        
        if current_page < total_pages:
            nav_buttons.append(InlineKeyboardButton("下一页 ➡️", callback_data=f"rank:{current_page + 1}"))
            
        keyboard.append(nav_buttons)
        
        return InlineKeyboardMarkup(keyboard)
    

    def _create_pagination_keyboard(
        self,
        keyword: str,
        works: list,
        current_page: int,
        total_count: int
    ) -> InlineKeyboardMarkup:
        """Create keyboard with detail buttons and pagination."""
        total_pages = (total_count + self.config.results_per_page - 1) // self.config.results_per_page
        
        keyboard = []
        
        # Detail buttons in rows of 5
        display_works = works[:10]
        detail_rows = []
        for i, work in enumerate(display_works, 1):
            work_id = work.get("id") or work.get("work_id") or work.get("pid")
            detail_rows.append(InlineKeyboardButton(str(i), callback_data=f"detail:{work_id}"))
            if len(detail_rows) == 5:
                keyboard.append(detail_rows)
                detail_rows = []
        if detail_rows:
            keyboard.append(detail_rows)
            
        # Pagination row
        nav_buttons = []
        if current_page > 1:
            nav_buttons.append(InlineKeyboardButton("⬅️ 上一页", callback_data=f"search:{keyword}:{current_page - 1}"))
        
        nav_buttons.append(InlineKeyboardButton(f"📄 {current_page}/{total_pages}", callback_data="noop"))
        
        if current_page < total_pages:
            nav_buttons.append(InlineKeyboardButton("下一页 ➡️", callback_data=f"search:{keyword}:{current_page + 1}"))
            
        keyboard.append(nav_buttons)
        
        return InlineKeyboardMarkup(keyboard)
    
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
        
        elif data.startswith("rank:"):
            parts = data.split(":")
            if len(parts) == 2:
                try:
                    page = int(parts[1])
                    await self._show_ranking(
                        update,
                        page=page,
                        message_id=query.message.message_id
                    )
                except ValueError:
                    await query.edit_message_text("❌ 无效的页码")
        
        elif data.startswith("tag:"):
            parts = data.split(":", 1)
            if len(parts) == 2:
                tag = parts[1]
                # Trigger a fresh search for this tag
                # We overwrite the query data since it's now a new context
                await self._perform_search(update, tag, page=1)
    
        elif data.startswith("copy_prompt:"):
            parts = data.split(":", 1)
            if len(parts) == 2:
                work_id = parts[1]
                await self._send_copyable_prompt(update, work_id)
    
        elif data.startswith("detail:"):
            parts = data.split(":")
            if len(parts) == 2:
                work_id = parts[1]
                await self._send_work_detail(update, work_id)
    
    
    async def _send_work_detail(self, update: Update, work_id: str, is_random: bool = False):
        """Fetch and send detailed work information with image and prompts."""
        query = update.callback_query
        
        if query:
            # Called from a button
            await query.answer("正在获取详情...")
            chat_id = query.message.chat_id
            message_thread_id = query.message.message_thread_id
        else:
            # Called from a command (like /random)
            chat_id = update.effective_chat.id
            message_thread_id = update.effective_message.message_thread_id if update.effective_message else None
        
        work = await self.api_client.get_work_detail(work_id)
        if not work:
            msg = "❌ 获取详情失败，请重试"
            if query:
                await query.message.reply_text(msg)
            else:
                await update.message.reply_text(msg)
            return
            
        # Extract metadata
        work_data = work.get("work") or work
        images = work.get("images", [])
        tags = work_data.get("tags") or []
        
        title = work_data.get("title") or "无标题"
        author = work_data.get("author_name") or "未知作者"
        
        # Find best image and prompt
        full_image_url = ""
        prompt = ""
        negative_prompt = ""
        seed = "N/A"
        sampler = "N/A"
        
        if images:
            img = images[0]
            full_image_url = self.api_client.get_full_image_url(img.get("image_path"))
            prompt = img.get("prompt_text") or ""
            
        # Parse AI JSON for more details
        import json
        ai_json_str = work_data.get("ai_json")
        if ai_json_str:
            try:
                ai_data = json.loads(ai_json_str)
                comment = ai_data.get("Comment", {})
                if not prompt:
                    prompt = comment.get("prompt") or ""
                negative_prompt = comment.get("uc") or ""
                seed = ai_data.get("Seed") or comment.get("seed") or seed
                sampler = ai_data.get("Sampler") or comment.get("sampler") or sampler
            except Exception:
                pass
                
        # Format message
        header = "🎲 <b>随机推荐</b>\n" if is_random else "🖼️ <b>作品详情</b>\n"
        caption = f"{header}"
        caption += f"标题：<b>{title}</b>\n"
        caption += f"作者：<b>{author}</b>\n"
        caption += f"ID：<code>{work_id}</code>\n"
        caption += "─" * 15 + "\n"
        
        if prompt:
            display_prompt = prompt if len(prompt) < 300 else prompt[:300] + "..."
            caption += f"📝 <b>正向词：</b>\n<code>{display_prompt}</code>\n\n"
            
        if negative_prompt:
            display_np = negative_prompt if len(negative_prompt) < 150 else negative_prompt[:150] + "..."
            caption += f"🚫 <b>反向词：</b>\n<code>{display_np}</code>\n\n"
            
        caption += f"🎲 种子：<code>{seed}</code> | 🧪 采样：{sampler}\n"
        caption += f"🔗 <a href='{self.api_client.get_work_url(work_id)}'>在网页查看原文</a>"

        # Create buttons
        keyboard_buttons = []
        
        # Row 1: Copy Prompt Button
        keyboard_buttons.append([InlineKeyboardButton("📋 复制全文提示词 (手机点此)", callback_data=f"copy_prompt:{work_id}")])
        
        # Rows 2+: Tag buttons
        if isinstance(tags, list):
            # Limit to top 10 tags
            row = []
            for tag in tags[:10]:
                row.append(InlineKeyboardButton(f"#{tag}", callback_data=f"tag:{tag}"))
                if len(row) == 2:
                    keyboard_buttons.append(row)
                    row = []
            if row:
                keyboard_buttons.append(row)
        
        keyboard = InlineKeyboardMarkup(keyboard_buttons)

        try:
            if full_image_url:
                if query:
                    await query.message.reply_photo(
                        photo=full_image_url,
                        caption=caption,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                else:
                    await self.app.bot.send_photo(
                        chat_id=chat_id,
                        photo=full_image_url,
                        caption=caption,
                        parse_mode="HTML",
                        reply_markup=keyboard,
                        message_thread_id=message_thread_id
                    )
            else:
                msg_call = query.message.reply_text if query else update.message.reply_text
                await msg_call(caption, parse_mode="HTML", reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Error sending detail: {e}", exc_info=True)
            err_msg = "❌ 发送失败，可能是图片链接失效"
            if query:
                await query.message.reply_text(err_msg)
            else:
                await update.message.reply_text(err_msg)

    async def _send_copyable_prompt(self, update: Update, work_id: str):
        """Send a separate message with the full prompt for easy copying."""
        query = update.callback_query
        await query.answer("正在生成可复制提示词...")
        
        work = await self.api_client.get_work_detail(work_id)
        if not work:
            await query.message.reply_text("❌ 获取咒语失败")
            return
            
        work_data = work.get("work") or work
        images = work.get("images", [])
        
        prompt = ""
        negative_prompt = ""
        
        if images:
            prompt = images[0].get("prompt_text") or ""
            
        import json
        ai_json_str = work_data.get("ai_json")
        if ai_json_str:
            try:
                ai_data = json.loads(ai_json_str)
                comment = ai_data.get("Comment", {})
                if not prompt:
                    prompt = comment.get("prompt") or ""
                negative_prompt = comment.get("uc") or ""
            except Exception:
                pass
        
        if not prompt and not negative_prompt:
             await query.message.reply_text("😕 该作品没有记录提示词信息")
             return

        # Format as a clean block for copying
        response = "📋 <b>完整提示词 (点击代码块即可复制):</b>\n\n"
        if prompt:
            response += f"<b>Prompt:</b>\n<code>{prompt}</code>\n\n"
        if negative_prompt:
            response += f"<b>Negative Prompt:</b>\n<code>{negative_prompt}</code>"
            
        await query.message.reply_text(response, parse_mode="HTML")
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
