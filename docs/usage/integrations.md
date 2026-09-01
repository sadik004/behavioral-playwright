# Webhook Integrations Usage Guide (Slack / Discord / n8n)

> **Last Verified Against Commit**: `68a3d1e`
> **Status**: [VERIFIED]

---

## 1. Dispatching Webhook Alerts

Send real HTTP notifications upon workflow completion:

```python
import asyncio
from bp_facade12 import BP

async def notify():
    async with BP() as bp:
        # Slack notification
        await bp.integrations.slack_webhook_notify_async(
            webhook_url="https://hooks.slack.com/services/...",
            message="*Crawl Pipeline Finished*: 45 items extracted."
        )

        # Discord notification
        await bp.integrations.discord_webhook_notify_async(
            webhook_url="https://discord.com/api/webhooks/...",
            message="Automation run completed successfully."
        )

        # n8n trigger
        await bp.integrations.n8n_webhook_trigger_async(
            webhook_url="https://n8n.example.com/webhook/test",
            payload={"job_id": 402, "status": "completed"}
        )

if __name__ == "__main__":
    asyncio.run(notify())
```
