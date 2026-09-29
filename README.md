# AutoSeller-Agent（Project Hermes）

旋轉拍賣台灣區（`tw.carousell.com`）個人賣家代理：在無官方 API 下實現商品自動刊登、聊聊議價回覆、訂單監控，Telegram Bot 為唯一操作介面。

## 使用

```bash
pip install -r requirements.txt
ruff check .
pytest -q
python main.py --check
python main.py --login
python main.py
```

首次使用先複製 `.env.example` 為 `.env` 並填入金鑰（`.env` 不進版控）。

## 核心約束

- `core/brain/` 禁止呼叫 `core/browser/`，跨層只傳 Pydantic `ListingContract`。
- 瀏覽器單一實例 FIFO，不多開並發。
- 任何低於 `floor_price` 的 LLM 回覆禁止發送。
- `storage/user_data/`、`.env`、金鑰一律不進版控。
- Captcha 只暫停加人工處理，不硬闖。
