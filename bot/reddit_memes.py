import praw
import logging
from random import choice
from config import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT
from strings import not_video_or_image

# Инициализируем PRAW
reddit = praw.Reddit(client_id=REDDIT_CLIENT_ID, client_secret=REDDIT_CLIENT_SECRET, user_agent=REDDIT_USER_AGENT)


# Функция для получения случайного мема по тегу с редита
def get_random_meme_by_tag(tag, sort, time_filter):
    # Выбираем посты из сообщества r/memes по тегу и сортировке
    subreddit = reddit.subreddit('memes')
    meme_posts = list(subreddit.search(tag, sort=sort, time_filter=time_filter, limit=50))

    if not meme_posts:
        raise Exception(
            f"Не удалось найти мемы по тегу '{tag}' с сортировкой '{sort}' и фильтром времени '{time_filter}'")

    # Выбираем случайный пост из найденных
    random_post = choice(meme_posts)

    # Проверяем, что пост содержит изображение или видео
    if random_post.url.endswith(('.jpg', '.jpeg', '.png')):
        logging.info("Мем является изображением")
        return 'image', random_post.url, random_post.title
    elif random_post.is_video:
        logging.info("Мем является видео/гифом")
        return 'video', random_post.media['reddit_video']['fallback_url'], random_post.title
    elif random_post.url.endswith(('.gif', '.gifv')):
        logging.info("Мем является видео/гифом")
        return 'video', random_post.url, random_post.title
    else:
        logging.info("Мем не является видео или изображением")
        raise Exception(not_video_or_image)
