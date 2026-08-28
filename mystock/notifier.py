import os
import json
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional


def _load_env_file():
    """Load key-value pairs from .env file into os.environ if present."""
    # Look for .env in current directory or project root
    env_paths = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parent.parent / ".env",
    ]
    for env_path in env_paths:
        if env_path.is_file():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip("'\"")
                            if k and k not in os.environ:
                                os.environ[k] = v
            except Exception:
                pass


_load_env_file()


class NotificationManager:
    """Manages notifications across Telegram, Slack, and Discord."""

    def __init__(
        self,
        telegram_token: Optional[str] = None,
        telegram_chat_id: Optional[str] = None,
        slack_webhook_url: Optional[str] = None,
        discord_webhook_url: Optional[str] = None,
    ):
        _load_env_file()
        self.telegram_token = telegram_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = telegram_chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.slack_webhook_url = slack_webhook_url or os.getenv("SLACK_WEBHOOK_URL")
        self.discord_webhook_url = discord_webhook_url or os.getenv("DISCORD_WEBHOOK_URL")


    def format_scan_report(
        self,
        alert_items: List[Dict[str, Any]],
        title: str = "📈 [myStock] 수급 신호 감지 알림",
    ) -> str:
        """Format detected divergence alerts into a clean readable message."""
        if not alert_items:
            return f"{title}\n\n✅ 특이 다이버전스 신호가 없습니다. (수급 안정)"

        lines = [title, "=" * 32]
        for item in alert_items:
            stock = item.get("stock", "Unknown")
            price = item.get("price", "0")
            avwap = item.get("avwap", "N/A")
            diff = item.get("diff", "0%")
            sig_type = item.get("sig_type", "")
            msg = item.get("message", "")
            date_str = item.get("date", "")

            icon = "★ [매수/매집]" if "강세" in sig_type or "BULL" in sig_type else "⚠️ [매도/경고]"
            lines.append(f"\n{icon} {stock}")
            lines.append(f"• 현재가: {price} (AVWAP {avwap}, {diff})")
            lines.append(f"• 시그널: {sig_type} ({date_str})")
            lines.append(f"• 세부내용: {msg}")

        lines.append("\n" + "=" * 32)
        lines.append("💡 myStock 대시보드에서 상세 차트를 확인하세요.")
        return "\n".join(lines)

    def send_telegram(self, message: str) -> bool:
        """Send message to Telegram."""
        if not self.telegram_token or not self.telegram_chat_id:
            return False

        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {
            "chat_id": self.telegram_chat_id,
            "text": message,
        }
        try:
            resp = requests.post(url, json=payload, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            print(f"[Notifier Error] Telegram send failed: {e}")
            return False

    def send_slack(self, message: str) -> bool:
        """Send message to Slack Incoming Webhook."""
        if not self.slack_webhook_url:
            return False

        payload = {"text": message}
        try:
            resp = requests.post(self.slack_webhook_url, json=payload, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            print(f"[Notifier Error] Slack send failed: {e}")
            return False

    def send_discord(self, message: str) -> bool:
        """Send message to Discord Webhook."""
        if not self.discord_webhook_url:
            return False

        payload = {"content": message}
        try:
            resp = requests.post(self.discord_webhook_url, json=payload, timeout=10)
            return resp.status_code in (200, 204)
        except Exception as e:
            print(f"[Notifier Error] Discord send failed: {e}")
            return False

    def broadcast(self, message: str) -> Dict[str, bool]:
        """Broadcast message to all configured notification channels."""
        results = {}
        if self.telegram_token and self.telegram_chat_id:
            results["telegram"] = self.send_telegram(message)
        if self.slack_webhook_url:
            results["slack"] = self.send_slack(message)
        if self.discord_webhook_url:
            results["discord"] = self.send_discord(message)

        if not results:
            print("[Notifier] 알림 채널(Telegram/Slack/Discord) 환경변수가 설정되지 않아 콘솔에 출력합니다.")
            print(message)
            results["console"] = True

        return results

    @staticmethod
    def get_latest_chat_id_from_telegram(bot_token: str) -> Optional[int]:
        """
        Fetch the latest Chat ID who sent a message to the bot.
        Useful when the user just created a bot and needs their Chat ID.
        """
        url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("result", [])
                if results:
                    last_update = results[-1]
                    message = last_update.get("message") or last_update.get("channel_post") or {}
                    chat = message.get("chat", {})
                    return chat.get("id")
        except Exception as e:
            print(f"[Notifier Error] Failed to get telegram updates: {e}")
        return None

