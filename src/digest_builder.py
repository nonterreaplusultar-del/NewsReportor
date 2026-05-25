import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def build_user_message(items: list[dict]) -> str:
    """Build the user message containing RSS items to be summarized."""
    lines = ["以下是最近抓取的 RSS 条目，请基于这些内容生成双语简报。", ""]
    for idx, item in enumerate(items, 1):
        lines.append(f"{idx}. [{item.get('category', '')}] {item.get('title', '')}")
        lines.append(f"   来源: {item.get('source', '')}")
        if item.get("published"):
            lines.append(f"   时间: {item.get('published', '')}")
        summary = item.get("summary", "")
        if summary:
            lines.append(f"   摘要: {summary[:300]}")
        lines.append("")
    return "\n".join(lines)


def build_prompt(items: list[dict]) -> list[dict]:
    """Build the messages array for the DeepSeek API call."""
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    system = f"""你是一位专业的双语信息编辑，服务于一位 25 岁中文母语年轻人。
读者希望提升未来竞争力、理解世界、提升技术判断力、审美能力和长期判断力。

当前时间: {now_str}

你的任务是根据提供的 RSS 条目，生成一份中英双语简报。

要求：
1. 不逐条罗列新闻；
2. 合并重复或高度相关的主题；
3. 删除低价值、重复、广告、招聘、纯公告类内容；
4. 选出 6 到 10 个真正值得关注的主题；
5. 每个主题包含：
   - 中文标题
   - English title
   - 中文总结：2 到 3 句
   - English summary: 1 to 2 sentences
   - Sources: 1 到 3 个来源名称
6. 最后输出：
   - 值得深读的 3 篇（标题 + 链接）
   - 对个人成长最重要的一条启发
7. 风格要求：
   - 准确、克制、简洁
   - 不鸡汤、不夸张、不像营销号
   - 不编造 RSS 条目中没有的信息
   - 信息不足时明确说信息不足
8. 输出格式严格遵循以下 Markdown 模板：

🌐 Personal Brief｜{{时间，格式: YYYY-MM-DD HH:MM}}

一句话总览：
中文：(一句话概括今日要点)
English: (one-line overview)

## 1. 中文主题标题
English title:

中文：(2 到 3 句中文总结)
English: (1 to 2 sentences English summary)

Sources:
- 来源1
- 来源2

## 2. ...

## 值得深读
1. [标题](链接)
2. [标题](链接)
3. [标题](链接)

## 今日启发
中文：
English:"""

    user = build_user_message(items)
    logger.info(
        "Built prompt: system=%d chars, user=%d chars, %d items",
        len(system), len(user), len(items),
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
