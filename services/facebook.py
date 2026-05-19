# services/facebook.py
import requests
import time
from django.conf import settings
from cryptography.fernet import Fernet
from core.exceptions import FacebookAPIError


class FacebookService:
    BASE_URL = f"https://graph.facebook.com/{settings.FACEBOOK_API_VERSION}"

    @staticmethod
    def get_app_access_token():
        """Get app access token using app ID and secret"""
        url = f"{FacebookService.BASE_URL}/oauth/access_token"
        params = {
            "client_id": settings.FACEBOOK_APP_ID,
            "client_secret": settings.FACEBOOK_APP_SECRET,
            "grant_type": "client_credentials",
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json().get("access_token")
        raise FacebookAPIError("Failed to get app access token")

    @staticmethod
    def get_long_lived_token(short_lived_token):
        """Exchange short-lived token for long-lived token"""
        url = f"{FacebookService.BASE_URL}/oauth/access_token"
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": settings.FACEBOOK_APP_ID,
            "client_secret": settings.FACEBOOK_APP_SECRET,
            "fb_exchange_token": short_lived_token,
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token"), data.get("expires_in")
        raise FacebookAPIError("Failed to exchange token")

    @staticmethod
    def get_user_pages(user_access_token):
        """Get list of pages managed by user"""
        url = f"{FacebookService.BASE_URL}/me/accounts"
        params = {
            "access_token": user_access_token,
            "fields": "id,name,username,category,picture,fan_count,access_token",
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json().get("data", [])
        raise FacebookAPIError("Failed to fetch pages")

    @staticmethod
    def decrypt_token(encrypted_token):
        """Decrypt page access token"""
        fernet = Fernet(settings.ENCRYPTION_KEY)
        return fernet.decrypt(encrypted_token.encode()).decode()

    @staticmethod
    def encrypt_token(token):
        """Encrypt page access token"""
        fernet = Fernet(settings.ENCRYPTION_KEY)
        return fernet.encrypt(token.encode()).decode()

    @staticmethod
    def sync_page_posts(page_id, page_token, since=None, limit=25):
        """Sync posts from Facebook page"""
        url = f"{FacebookService.BASE_URL}/{page_id}/posts"
        params = {
            "access_token": (
                FacebookService.decrypt_token(page_token) if page_token else page_token
            ),
            "fields": "id,message,created_time,permalink_url,attachments{type,media,url},likes.summary(true),comments.summary(true),shares",
            "limit": limit,
        }
        if since:
            params["since"] = since

        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            # Rate limit - exponential backoff
            time.sleep(60)
            return FacebookService.sync_page_posts(page_id, page_token, since, limit)
        else:
            raise FacebookAPIError(f"Failed to sync posts: {response.text}")

    @staticmethod
    def sync_post_comments(post_id, page_token, limit=100):
        """Sync comments for a specific post"""
        url = f"{FacebookService.BASE_URL}/{post_id}/comments"
        params = {
            "access_token": (
                FacebookService.decrypt_token(page_token) if page_token else page_token
            ),
            "fields": "id,from{id,name,picture},message,created_time,comments{id,from,message,created_time}",
            "limit": limit,
        }

        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            time.sleep(60)
            return FacebookService.sync_post_comments(post_id, page_token, limit)
        else:
            raise FacebookAPIError(f"Failed to sync comments: {response.text}")

    @staticmethod
    def reply_to_comment(comment_id, page_token, message):
        """Reply to a comment on Facebook"""
        url = f"{FacebookService.BASE_URL}/{comment_id}/comments"
        params = {
            "access_token": (
                FacebookService.decrypt_token(page_token) if page_token else page_token
            ),
            "message": message,
        }

        response = requests.post(url, params=params)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            time.sleep(30)
            return FacebookService.reply_to_comment(comment_id, page_token, message)
        else:
            raise FacebookAPIError(f"Failed to reply to comment: {response.text}")
