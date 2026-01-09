"""
Statistics tracking module for the Telegram bot.
Tracks post generation, active users, and popular topics.
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from collections import Counter
import logging

logger = logging.getLogger(__name__)

STATS_FILE = "bot_statistics.json"


class BotStatistics:
    """Manages bot usage statistics"""
    
    def __init__(self, stats_file: str = STATS_FILE):
        self.stats_file = stats_file
        self.stats = self._load_stats()
    
    def _load_stats(self) -> Dict:
        """Load statistics from file or create new if doesn't exist"""
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading statistics: {e}")
                return self._create_default_stats()
        else:
            return self._create_default_stats()
    
    def _create_default_stats(self) -> Dict:
        """Create default statistics structure"""
        return {
            "total_posts": 0,
            "text_only_posts": 0,
            "posts_with_images": 0,
            "active_users": {},  # user_id: last_activity_timestamp
            "topics": [],  # list of all topics requested
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }
    
    def _save_stats(self):
        """Save statistics to file"""
        try:
            self.stats["last_updated"] = datetime.now().isoformat()
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving statistics: {e}")
    
    def record_post(self, user_id: int, topic: str, post_type: str = "text"):
        """
        Record a post generation
        
        Args:
            user_id: Telegram user ID
            topic: Topic of the post
            post_type: "text" or "images"
        """
        self.stats["total_posts"] += 1
        
        if post_type == "text":
            self.stats["text_only_posts"] += 1
        elif post_type == "images":
            self.stats["posts_with_images"] += 1
        
        # Update active users
        self.stats["active_users"][str(user_id)] = datetime.now().isoformat()
        
        # Add topic
        self.stats["topics"].append({
            "topic": topic,
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id
        })
        
        self._save_stats()
        logger.info(f"Recorded {post_type} post for user {user_id}: {topic}")
    
    def get_active_users_count(self) -> int:
        """Get count of active users"""
        return len(self.stats["active_users"])
    
    def get_popular_topics(self, top_n: int = 10) -> List[tuple]:
        """
        Get most popular topics
        
        Args:
            top_n: Number of top topics to return
            
        Returns:
            List of (topic, count) tuples
        """
        topics = [entry["topic"] for entry in self.stats["topics"]]
        topic_counter = Counter(topics)
        return topic_counter.most_common(top_n)
    
    def get_report(self) -> str:
        """
        Generate a formatted statistics report
        
        Returns:
            Formatted statistics string
        """
        popular_topics = self.get_popular_topics(5)
        
        report = (
            f"📊 <b>Статистика бота</b>\n\n"
            f"📝 <b>Общее количество постов:</b> {self.stats['total_posts']}\n"
            f"  • Только текст: {self.stats['text_only_posts']}\n"
            f"  • С изображениями: {self.stats['posts_with_images']}\n\n"
            f"👥 <b>Активные пользователи:</b> {self.get_active_users_count()}\n\n"
            f"🔥 <b>Популярные темы:</b>\n"
        )
        
        if popular_topics:
            for i, (topic, count) in enumerate(popular_topics, 1):
                report += f"  {i}. {topic} ({count} раз)\n"
        else:
            report += "  Пока нет данных\n"
        
        report += f"\n📅 Последнее обновление: {self.stats['last_updated'][:19]}"
        
        return report


# Global instance
stats_tracker = BotStatistics()
