# services/ai_analyzer.py
import json
import re
from django.conf import settings
from openai import OpenAI
from core.exceptions import AIServiceError

client = OpenAI(api_key=settings.OPENAI_API_KEY)


class AIAnalyzer:
    @staticmethod
    def analyze_comment(comment_text, language="ar"):
        """Analyze comment for intent, sentiment, and lead score"""
        try:
            system_prompt = """You are an AI assistant for social media customer service. 
            Analyze this Arabic/English Facebook comment. Return ONLY valid JSON with these fields:
            {
                "intent": "price|details|booking|location|complaint|phone|general|spam|positive_feedback|negative_feedback|question",
                "intent_confidence": 0.0-1.0,
                "sentiment": "very_positive|positive|neutral|negative|very_negative",
                "sentiment_confidence": 0.0-1.0,
                "lead_score": 0-100 (likelihood to become customer),
                "phone": null or extracted phone number,
                "email": null or extracted email,
                "location": null or extracted location,
                "keywords": [array of keywords],
                "language": "ar|en|mixed",
                "model_version": "gpt-4"
            }
            
            Lead score criteria:
            - Price inquiries: 70-90
            - Booking requests: 80-95
            - Phone/contact requests: 75-85
            - Complaints: 30-50
            - General questions: 40-60
            - Spam: 0-10
            - Positive feedback: 20-40
            
            Handle Egyptian Arabic slang and common expressions."""

            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": comment_text},
                ],
                temperature=0.3,
                max_tokens=500,
            )

            result = json.loads(response.choices[0].message.content)
            result["tokens_used"] = response.usage.total_tokens
            return result

        except json.JSONDecodeError:
            # Fallback to rule-based analysis
            return AIAnalyzer._rule_based_analysis(comment_text)
        except Exception as e:
            raise AIServiceError(f"AI analysis failed: {str(e)}")

    @staticmethod
    def _rule_based_analysis(comment_text):
        """Fallback rule-based analysis when AI fails"""
        text_lower = comment_text.lower()

        # Intent detection
        intent = "general"
        intent_confidence = 0.5

        price_keywords = ["سعر", "بكام", "التكلفة", "price", "cost", "how much", "كم"]
        booking_keywords = ["حجز", "احجز", "book", "reserve", "موعد", "appointment"]
        complaint_keywords = ["مشكلة", "سيء", "bad", "complaint", "شكوى", "مش"]
        phone_keywords = ["رقم", "phone", "اتصل", "call", "موبايل", "mobile"]

        for keyword in price_keywords:
            if keyword in text_lower:
                intent = "price"
                intent_confidence = 0.8
                break

        # Sentiment
        positive_words = ["ممتاز", "جميل", "great", "awesome", "شكرا", "thanks"]
        negative_words = ["سيء", "bad", "terrible", "مشكلة", "problem"]

        sentiment = "neutral"
        sentiment_confidence = 0.5

        if any(word in text_lower for word in positive_words):
            sentiment = "positive"
            sentiment_confidence = 0.7
        elif any(word in text_lower for word in negative_words):
            sentiment = "negative"
            sentiment_confidence = 0.7

        # Lead score
        lead_score = 30
        if intent == "price":
            lead_score = 75
        elif intent == "booking":
            lead_score = 85
        elif intent == "complaint":
            lead_score = 20

        # Extract phone/email with regex
        phone_match = re.search(r"01[0-2]\d{8}", comment_text)
        email_match = re.search(
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", comment_text
        )

        return {
            "intent": intent,
            "intent_confidence": intent_confidence,
            "sentiment": sentiment,
            "sentiment_confidence": sentiment_confidence,
            "lead_score": lead_score,
            "phone": phone_match.group(0) if phone_match else None,
            "email": email_match.group(0) if email_match else None,
            "location": None,
            "keywords": [],
            "language": (
                "ar" if any("\u0600" <= c <= "\u06ff" for c in comment_text) else "en"
            ),
            "model_version": "rule-based-fallback",
        }

    @staticmethod
    def generate_reply(comment_text, intent, sentiment, tone="professional"):
        """Generate AI reply for a comment"""
        try:
            system_prompt = f"""You are a customer service rep. Generate Arabic reply (Egyptian dialect if appropriate) to this Facebook comment.
            Comment: {comment_text}
            Intent: {intent}
            Sentiment: {sentiment}
            Tone: {tone}
            
            Rules:
            - Be friendly and personal
            - Address the specific intent
            - Keep under 3 sentences
            - Use emojis appropriately
            - Don't mention you're AI
            - If price inquiry: acknowledge and ask for DM details
            - If complaint: apologize and offer resolution
            - If booking: ask for preferred time
            - Use Egyptian Arabic dialect naturally"""

            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "Generate a reply"},
                ],
                temperature=0.7,
                max_tokens=300,
            )

            return {
                "reply": response.choices[0].message.content,
                "tokens_used": response.usage.total_tokens,
            }

        except Exception as e:
            raise AIServiceError(f"AI reply generation failed: {str(e)}")
