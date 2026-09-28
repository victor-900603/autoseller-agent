import logging
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from core.contracts import Job, JobType
from core.orchestrator.job_queue import JobQueue
from core.orchestrator.scheduler import Scheduler
from core.orchestrator.state_store import StateStore

logger = logging.getLogger("autoseller.bot")

APPROVE_PREFIX = "approve:"
REJECT_PREFIX = "reject:"


class TelegramApp:
    """操作介面，白名單外指令直接忽略。"""

    def __init__(
        self,
        token: str,
        admin_ids: set[int],
        store: StateStore,
        queue: JobQueue,
        scheduler: Scheduler,
    ) -> None:
        """注入token、管理員、儲存、佇列與排程器，不啟動輪詢。"""
        self._token = token
        self._admin_ids = admin_ids
        self._store = store
        self._queue = queue
        self._scheduler = scheduler

    def is_admin(self, user_id: int) -> bool:
        """是否為白名單管理員。"""
        return user_id in self._admin_ids

    async def start_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """回應啟用指令，非管理員忽略。"""
        if not self.is_admin(update.effective_user.id):
            logger.warning("忽略非管理員指令：%s", update.effective_user.id)
            return
        await update.message.reply_text("代理運行中，用 /pending 查看待審核。")

    async def pending_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """列出待審核草稿，非管理員忽略。"""
        if not self.is_admin(update.effective_user.id):
            return
        products = await self._store.list_products("DRAFT")
        if not products:
            await update.message.reply_text("目前無待審核。")
            return
        lines = [
            f"{p['id']}｜{p['title']}｜建議 {p['suggested_price']}／底價 {p['floor_price']}"
            for p in products
        ]
        await update.message.reply_text("\n".join(lines))

    async def status_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """查詢單一商品狀態，非管理員忽略。"""
        if not self.is_admin(update.effective_user.id):
            return
        if not context.args:
            await update.message.reply_text("用法：/status <product_id>")
            return
        product = await self._store.get_product(context.args[0])
        if product is None:
            await update.message.reply_text("查無此商品。")
            return
        await update.message.reply_text(
            f"{product['id']}｜{product['title']}｜{product['status']}｜"
            f"建議 {product['suggested_price']}／底價 {product['floor_price']}"
        )

    async def pause_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """暫停刊登消費，非管理員忽略。"""
        if not self.is_admin(update.effective_user.id):
            return
        self._scheduler.pause()
        await update.message.reply_text("已暫停刊登消費。")

    async def resume_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """恢復刊登消費，非管理員忽略。"""
        if not self.is_admin(update.effective_user.id):
            return
        self._scheduler.resume()
        await update.message.reply_text("已恢復刊登消費。")

    def review_keyboard(self, product_id: str) -> InlineKeyboardMarkup:
        """審核按鈕，未核准不入列。"""
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("核准刊登", callback_data=f"{APPROVE_PREFIX}{product_id}"),
                    InlineKeyboardButton("退回", callback_data=f"{REJECT_PREFIX}{product_id}"),
                ]
            ]
        )

    async def review_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """處理審核按鈕，核准才入列。"""
        query = update.callback_query
        if not self.is_admin(query.from_user.id):
            return
        data = query.data or ""
        if data.startswith(APPROVE_PREFIX):
            product_id = data[len(APPROVE_PREFIX):]
            await self._queue.put(
                Job(job_type=JobType.LISTING, payload={"product_id": product_id},
                    idempotency_key=f"listing:{product_id}")
            )
            await query.answer("已排入刊登。")
        elif data.startswith(REJECT_PREFIX):
            product_id = data[len(REJECT_PREFIX):]
            await self._store.log_execution(
                "LISTING", "FAILURE", product_id=product_id, error_message="人工退回"
            )
            await query.answer("已退回。")
        await query.edit_message_reply_markup(reply_markup=None)

    async def notify_admins(self, text: str, screenshot: str | Path | None = None) -> None:
        """向管理員推播，附截圖走圖片通道。"""
        application = getattr(self, "_application", None)
        if application is None:
            return
        for admin_id in self._admin_ids:
            if screenshot is None:
                await application.bot.send_message(chat_id=admin_id, text=text)
            else:
                with open(screenshot, "rb") as photo:
                    await application.bot.send_photo(chat_id=admin_id, photo=photo, caption=text)

    def build_app(self) -> Application:
        """組裝指令路由，不啟動輪詢。"""
        application = (
            Application.builder().token(self._token).build()
        )
        application.add_handler(CommandHandler("start", self.start_cmd))
        application.add_handler(CommandHandler("pending", self.pending_cmd))
        application.add_handler(CommandHandler("status", self.status_cmd))
        application.add_handler(CommandHandler("pause", self.pause_cmd))
        application.add_handler(CommandHandler("resume", self.resume_cmd))
        application.add_handler(CallbackQueryHandler(self.review_callback))
        self._application = application
        return application

    async def run(self) -> None:
        """啟動輪詢（需真實token與網路）。"""
        await self.build_app().run_polling()
