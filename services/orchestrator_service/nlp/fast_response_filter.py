import re
import random
from typing import Optional, List, Dict
from core.logger import get_logger

logger = get_logger("fast_response_filter")

def normalize_arabic(text: str) -> str:
    """
    Cleans and normalizes Arabic text to make matching highly robust.
    - Removes Arabic tashkeel (diacritics).
    - Standardizes Alef (أ, إ, آ -> ا).
    - Standardizes Teh Marbuta (ة -> ه).
    - Standardizes Alef Maksura (ى -> ي).
    - Removes punctuation marks and excessive whitespaces.
    """
    if not text:
        return ""
    
    # Remove Arabic diacritics
    text = re.sub(r'[\u064B-\u0652]', '', text)
    
    # Normalize Alef variations to bare Alef
    text = re.sub(r'[أإآ]', 'ا', text)
    
    # Normalize Teh Marbuta to Heh
    text = re.sub(r'ة', 'ه', text)
    
    # Normalize Alef Maksura to Yeh
    text = re.sub(r'ى', 'y', text)  # Temporary intermediate to avoid conflict
    text = re.sub(r'ي', 'ي', text)
    text = re.sub(r'y', 'ي', text)
    
    # Remove punctuation & special characters (Arabic and English)
    text = re.sub(r'[?؟\.,!،\-\_\(\)\[\]\{\}\:\;\/\*\"\'\’]', ' ', text)
    
    # Normalize excessive whitespaces
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip().lower()

class FastResponseFilter:
    """
    Independent filtering system that intercepts user queries immediately upon arrival.
    If the query matches predefined greetings or simple FAQ patterns, it returns a 
    randomly selected appropriate response, bypassing RAG/LLM pipelines.
    
    Responses are separated into language-specific dictionaries (_arabic_responses
    and _english_responses) so that the match logic can skip irrelevant entries
    based on a quick language detection heuristic.
    """
    def __init__(self):
        # ─────────────── Arabic Responses ───────────────
        # Keys are pre-normalized Arabic text for direct mapping comparison
        self._arabic_responses: Dict[str, List[str]] = {
            "السلام عليكم": [
                "وعليكم السلام ورحمة الله وبركاته! كيف يمكنني مساعدتك اليوم؟ 😊",
                "وعليكم السلام ورحمة الله وبركاته. أهلاً بك في AskHR، كيف يمكنني خدمتك؟",
                "وعليكم السلام ورحمة الله وبركاته. كيف أستطيع مساعدتك اليوم في شؤون الموارد البشرية؟"
            ],
            "سلام": [
                "وعليكم السلام ورحمة الله وبركاته، كيف يمكنني مساعدتك اليوم؟",
                "أهلاً بك! أتمنى أن تكون بصحة جيدة. كيف يمكنني خدمتك؟ 😊",
                "وعليكم السلام، أهلاً بك في AskHR! كيف أستطيع مساعدتك؟"
            ],
            "سلام عليكم": [
                "وعليكم السلام ورحمة الله وبركاته! أهلاً بك. كيف يمكنني مساعدتك اليوم؟",
                "وعليكم السلام ورحمة الله وبركاته. كيف أستطيع خدمتك اليوم؟ 😊"
            ],
            "مرحبا": [
                "أهلاً بك! كيف يمكنني مساعدتك اليوم؟ 😊",
                "مرحباً بك! أتمنى لك يوماً سعيداً. كيف يمكنني خدمتك؟",
                "أهلاً وسهلاً بك في AskHR! كيف يمكنني مساعدتك اليوم؟"
            ],
            "اهلا": [
                "أهلاً بك! كيف يمكنني مساعدتك اليوم؟",
                "مرحباً بك! كيف يمكنني خدمتك؟ 😊",
                "أهلاً وسهلاً! كيف أستطيع مساعدتك اليوم؟"
            ],
            "هلا": [
                "أهلاً بك! كيف يمكنني مساعدتك اليوم؟",
                "يا مرحباً! كيف يمكنني خدمتك؟ 😊",
                "أهلاً وسهلاً! تفضل، كيف أستطيع مساعدتك؟"
            ],
            "يا هلا": [
                "أهلاً بك! كيف يمكنني مساعدتك اليوم؟",
                "يا مرحباً! كيف يمكنني خدمتك؟ 😊",
                "أهلاً وسهلاً! تفضل، كيف أستطيع مساعدتك؟"
            ],
            "صباح الخير": [
                "صباح النور والسرور! كيف يمكنني مساعدتك اليوم؟ ☀️",
                "صباح الخير! أتمنى لك يوماً جميلاً وموفقاً. كيف يمكنني خدمتك؟"
            ],
            "صباحك": [
                "صباح النور والسرور! أتمنى لك يوماً سعيداً وموفقاً. كيف أستطيع خدمتك اليوم؟ ☀️",
                "صباح النور! أهلاً بك. كيف يمكنني مساعدتك اليوم؟"
            ],
            "صباحك ورد": [
                "صباح النور والسرور! أتمنى لك يوماً سعيداً وموفقاً. كيف أستطيع خدمتك اليوم؟ ☀️",
                "صباح النور والجمال! أهلاً بك. كيف يمكنني مساعدتك اليوم؟"
            ],
            "صباحك فل": [
                "صباح النور والسرور! أتمنى لك يوماً سعيداً وموفقاً. كيف أستطيع خدمتك اليوم؟ ☀️",
                "صباح النور والجمال! أهلاً بك. كيف يمكنني مساعدتك اليوم؟"
            ],
            "مساء الخير": [
                "مساء النور والسرور! كيف يمكنني مساعدتك اليوم؟ 🌙",
                "مساء الخير! أتمنى لك وقتاً طيباً. كيف يمكنني خدمتك؟"
            ],
            "كيف حالك": [
                "أنا بخير والحمد لله! شكراً لسؤالك. كيف يمكنني مساعدتك اليوم في شؤون الموارد البشرية؟ 😊",
                "بأفضل حال، شكراً لك! كيف يمكنني خدمتك اليوم؟"
            ],
            "كيف الحال": [
                "أنا بخير والحمد لله! شكراً لسؤالك. كيف يمكنني مساعدتك اليوم في شؤون الموارد البشرية؟ 😊",
                "بأفضل حال، شكراً لك! كيف يمكنني خدمتك اليوم؟"
            ],
            "شلونك": [
                "أنا بخير والحمد لله! شكراً لسؤالك. كيف يمكنني مساعدتك اليوم؟ 😊",
                "بأفضل حال، شكراً لك! كيف يمكنني خدمتك اليوم?"
            ],
            "كيفك": [
                "أنا بخير والحمد لله! شكراً لسؤالك. كيف يمكنني مساعدتك اليوم؟ 😊",
                "بأفضل حال، شكراً لك! كيف يمكنني خدمتك اليوم؟"
            ],
            "كل عام وانت بخير": [
                "وأنت بألف خير وصحة وسلامة! أعاده الله علينا وعليكم بالخير والبركات. 🌸 كيف يمكنني مساعدتك اليوم؟",
                "كل عام وأنت بصحة وعافية! أتمنى لك أياماً مباركة وسعيدة. كيف أستطيع خدمتك اليوم? 😊",
                "وأنت بخير وصحة وسلامة! عساكم من عواده. كيف يمكنني خدمتك اليوم؟"
            ],
            "كل عام وانتم بخير": [
                "وأنتم بألف خير وصحة وسلامة! أعاده الله علينا وعليكم بالخير والبركات. 🌸 كيف يمكنني مساعدتك اليوم؟",
                "كل عام وأنتم بصحة وعافية! أتمنى لكم أياماً مباركة وسعيدة. كيف أستطيع خدمتكم اليوم؟ 😊",
                "وأنتم بخير وصحة وسلامة! عساكم من عواده. كيف يمكنني خدمتكم اليوم؟"
            ],
            "عيد مبارك": [
                "علينا وعليكم بالخير والبركات! عيد مبارك وكل عام وأنت بخير وصحة وسلامة. 🌸 كيف يمكنني مساعدتك اليوم؟",
                "عيد مبارك سعيد وكل عام وأنت بألف خير! كيف أستطيع خدمتك اليوم؟ 😊"
            ],
            "عساكم من عواده": [
                "علينا وعليكم بالخير والبركات! عيد مبارك وكل عام وأنت بخير وصحة وسلامة. 🌸 كيف يمكنني مساعدتك اليوم؟",
                "عيد مبارك سعيد وكل عام وأنت بألف خير! كيف أستطيع خدمتك اليوم؟ 😊"
            ],
            "من انت": [
                "أنا AskHRPro، المساعد الذكي لقسم Ask HR والخدمات المشتركة بمجموعة هائل سعيد أنعم. كيف يمكنني مساعدتك اليوم؟ 😊",
                "أهلاً بك! أنا خبير الموارد البشرية الرقمي الخاص بك (AskHRPro) التابع لقسم نظم معلومات الموارد البشرية (HRIS) والخدمات المشتركة في مجموعة HSA. كيف أستطيع خدمتك اليوم؟",
                "أنا خبير الموارد البشرية في مجموعة هائل سعيد أنعم (HSA Group). وظيفتي هي تقديم المعلومات والمساعدة حول سياسات العمل واللوائح والإجراءات المتعلقة بالموظفين بالتنسيق مع الخدمات المشتركة وقسم HRIS. كيف يمكنني مساعدتك اليوم؟ 😊"
            ],
            "ما وظيفتك": [
                "وظيفتي هي مساعدتك وتسهيل استفساراتك حول شؤون الموظفين في مجموعة HSA. تفضل بطرح سؤالك! 👍",
                "أقوم بمساعدتك في الاستعلام عن لوائح وسياسات الموارد البشرية، ومعالجة المعاملات مثل طلب الإجازة أو كشوفات الراتب مباشرة بالتنسيق مع إدارة الموارد البشرية الرقمية (HRIS) والخدمات المشتركة.",
                "دوري هنا هو تيسير الوصول لخدمات الموارد البشرية بمجموعة هائل سعيد أنعم؛ حيث يمكنني شرح السياسات واللوائح، والإجابة عن استفسارات الرواتب والبدلات، أو حتى البدء في تسجيل طلبات الإجازات نيابة عنك بالتنسيق مع قسم HRIS. كيف تبغى أساعدك اليوم؟ 😊"
            ],
            "ما هي وظيفتك": [
                "وظيفتي هي مساعدتك وتسهيل استفساراتك حول شؤون الموظفين في مجموعة HSA. تفضل بطرح سؤالك! 👍",
                "أقوم بمساعدتك في الاستعلام عن لوائح وسياسات الموارد البشرية، ومعالجة المعاملات مثل طلب الإجازة أو كشوفات الراتب مباشرة بالتنسيق مع إدارة الموارد البشرية الرقمية (HRIS) والخدمات المشتركة.",
                "دوري هنا هو تيسير الوصول لخدمات الموارد البشرية بمجموعة هائل سعيد أنعم؛ حيث يمكنني شرح السياسات واللوائح، والإجابة عن استفسارات الرواتب والبدلات، أو حتى البدء في تسجيل طلبات الإجازات نيابة عنك بالتنسيق مع قسم HRIS. كيف تبغى أساعدك اليوم؟ 😊"
            ],
            "ماذا تعمل": [
                "وظيفتي هي مساعدتك وتسهيل استفساراتك حول شؤون الموظفين في مجموعة HSA. تفضل بطرح سؤالك! 👍",
                "أقوم بمساعدتك في الاستعلام عن لوائح وسياسات الموارد البشرية، ومعالجة المعاملات مثل طلب الإجازة أو كشوفات الراتب مباشرة بالتنسيق مع إدارة الموارد البشرية الرقمية (HRIS) والخدمات المشتركة.",
                "دوري هنا هو تيسير الوصول لخدمات الموارد البشرية بمجموعة هائل سعيد أنعم؛ حيث يمكنني شرح السياسات واللوائح، والإجابة عن استفسارات الرواتب والبدلات، أو حتى البدء في تسجيل طلبات الإجازات نيابة عنك بالتنسيق مع قسم HRIS. كيف تبغى أساعدك اليوم؟ 😊"
            ],
            "ما عملك": [
                "وظيفتي هي مساعدتك وتسهيل استفساراتك حول شؤون الموظفين في مجموعة HSA. تفضل بطرح سؤالك! 👍",
                "أقوم بمساعدتك في الاستعلام عن لوائح وسياسات الموارد البشرية، ومعالجة المعاملات مثل طلب الإجازة أو كشوفات الراتب مباشرة بالتنسيق مع إدارة الموارد البشرية الرقمية (HRIS) والخدمات المشتركة.",
                "دوري هنا هو تيسير الوصول لخدمات الموارد البشرية بمجموعة هائل سعيد أنعم؛ حيث يمكنني شرح السياسات واللوائح، والإجابة عن استفسارات الرواتب والبدلات، أو حتى البدء في تسجيل طلبات الإجازات نيابة عنك بالتنسيق مع قسم HRIS. كيف تبغى أساعدك اليوم؟ 😊"
            ],
            "كيف تساعدني": [
                "يمكنني مساعدتك في شرح سياسات الموارد البشرية والإجازات، تقديم طلبات الإجازة، والاستعلام عن كشوفات الراتب الشهري. تفضل بالاستفسار!",
                "بصفتي مساعدك الافتراضي للموارد البشرية، يمكنني توفير الوقت عليك بالبحث في لوائح وسياسات مجموعة HSA، أو مساعدتك في رفع طلب إجازة والتحقق من راتبك دون الحصول على عناء مراجعة قسم شؤون الموظفين يدوياً. 👍",
                "أنا هنا لأكون مستشارك الشخصي في شؤون الموظفين بـ HSA Group. يمكنني إرشادك لمتطلبات أي معاملة وتوضيح القوانين الإدارية الخاصة بالشركة، بالإضافة للربط المباشر مع خدمات SuccessFactors كتقديم طلب إجازة أو سحب كشف راتب شهري بالتنسيق مع قسم الخدمات المشتركة ونظم معلومات الموارد البشرية HRIS."
            ],
            "ما هو هذا النظام": [
                "أنا AskHRPro، المساعد الذكي لقسم Ask HR والخدمات المشتركة بمجموعة هائل سعيد أنعم. كيف يمكنني مساعدتك اليوم؟ 😊",
                "أهلاً بك! أنا خبير الموارد البشرية الرقمي الخاص بك (AskHRPro) التابع لقسم نظم معلومات الموارد البشرية (HRIS) والخدمات المشتركة في مجموعة HSA. كيف أستطيع خدمتك اليوم؟",
                "أنا خبير الموارد البشرية في مجموعة هائل سعيد أنعم (HSA Group). وظيفتي هي تقديم المعلومات والمساعدة حول سياسات العمل واللوائح والإجراءات المتعلقة بالموظفين بالتنسيق مع الخدمات المشتركة وقسم HRIS. كيف يمكنني مساعدتك اليوم؟ 😊"
            ],
            "شكرا": [
                "على الرحب والسعة! أنا هنا دائماً للمساعدة. 😊",
                "عفواً! يسعدني دائماً تقديم العون لك. أتمنى لك يوماً رائعاً! 👍",
                "لا شكر على واجب! إذا كان لديك أي استفسار آخر فلا تتردد في طرحه."
            ],
            "شكرا لك": [
                "على الرحب والسعة! أنا هنا دائماً للمساعدة. 😊",
                "عفواً! يسعدني دائماً تقديم العون لك. أتمنى لك يوماً رائعاً! 👍",
                "لا شكر على واجب! إذا كان لديك أي استفسار آخر فلا تتردد في طرحه."
            ],
            "تسلم": [
                "الله يسلمك ويحفظك! أنا هنا دائماً للمساعدة. 😊",
                "عفواً! يسعدني دائماً تقديم العون لك."
            ],
            "يعطيك العافيه": [
                "الله يعافيك ويقويك! يسعدني دائماً تقديم المساعدة. كيف أستطيع خدمتك اليوم؟ 😊",
                "الله يعافيك! أتمنى لك يوماً سعيداً."
            ]
        }

        # ─────────────── English Responses ───────────────
        # Keys are lowercase, punctuation-free English text
        # ─────────────── English Responses ───────────────
        # Keys are lowercase, punctuation-free English text
        self._english_responses: Dict[str, List[str]] = {
            # Basic greetings
            "hello": [
                "Hello! Welcome to AskHR. How can I help you today? 😊",
                "Hi there! How can I assist you with your HR inquiry?",
                "Hello and welcome! I'm your AskHR assistant. What can I do for you today?"
            ],
            "hi": [
                "Hi! How can I help you today? 😊",
                "Hi there! Welcome to AskHR. How can I assist you?",
                "Hey! I'm here to help with any HR questions. What do you need?"
            ],
            "hey": [
                "Hey! How can I help you today? 😊",
                "Hey there! Welcome to AskHR. How can I assist you?",
                "Hi! What can I do for you today?"
            ],
            "hey there": [
                "Hey there! How can I help you today? 😊",
                "Hello! Welcome to AskHR. What can I assist you with?",
                "Hi! I'm here to help. What do you need?"
            ],
            "greetings": [
                "Greetings! Welcome to AskHR. How can I assist you today? 😊",
                "Hello and welcome! How may I help you?",
                "Greetings! I'm here to help with your HR needs. What can I do for you?"
            ],
            "howdy": [
                "Howdy! Welcome to AskHR. How can I help you today? 😊",
                "Hey there! How can I assist you today?"
            ],

            # Time-of-day greetings
            "good morning": [
                "Good morning! Wishing you a wonderful day ahead. How can I help you today? ☀️",
                "Good morning! Welcome to AskHR. How may I assist you?",
                "Morning! Hope you're having a great start to your day. How can I help? ☀️"
            ],
            "morning": [
                "Good morning! How can I assist you today? ☀️",
                "Morning! Wishing you a great day. How can I help?"
            ],
            "good afternoon": [
                "Good afternoon! How can I help you today? 😊",
                "Good afternoon! Welcome to AskHR. How may I assist you?"
            ],
            "good evening": [
                "Good evening! How can I help you today? 🌙",
                "Good evening! Welcome to AskHR. How may I assist you?",
                "Good evening! I hope you've had a great day. How can I help? 🌙"
            ],
            "good night": [
                "Good night! If you have any questions before you go, I'm happy to help 🌙",
                "Good night! Feel free to come back anytime you need assistance."
            ],

            # How-are-you variants
            "how are you": [
                "I'm doing great, thank you for asking! How can I help you today with your HR needs? 😊",
                "I'm doing well, thanks! How can I assist you today?"
            ],
            "how are you doing": [
                "I'm doing great, thank you for asking! How can I assist you today? 😊",
                "Doing well, thanks! What can I help you with?"
            ],
            "how is it going": [
                "It's going well, thank you! How can I help you today? 😊",
                "All good on my end! How can I assist you?"
            ],
            "whats up": [
                "I'm here and ready to help! What can I do for you today? 😊",
                "Not much, just ready to assist! What do you need help with?"
            ],

            # Identity / Role questions
            "who are you": [
                "I'm AskHRPro, the AI assistant for the HR and Shared Services department at HSA Group. How can I help you today? 😊",
                "Welcome! I'm your digital HR expert (AskHRPro) from the HRIS and Shared Services division at HSA Group. How can I assist you?",
                "I'm the HR expert for Hayel Saeed Anam Group (HSA Group). My role is to provide information and assistance regarding work policies, regulations, and employee-related procedures in coordination with Shared Services and HRIS. How can I help you today? 😊"
            ],
            "what do you do": [
                "My role is to help you with your HR inquiries at HSA Group. Feel free to ask me anything! 👍",
                "I assist you with HR policies, leave requests, salary slips, and employee-related procedures in coordination with the HRIS and Shared Services departments.",
                "I'm here to make HR services at HSA Group more accessible. I can explain company policies, answer questions about salaries and allowances, and even help you submit leave requests in coordination with HRIS. How can I help you today? 😊"
            ],
            "what is your job": [
                "My role is to help you with your HR inquiries at HSA Group. Feel free to ask me anything! 👍",
                "I assist you with HR policies, leave requests, salary slips, and employee-related procedures in coordination with the HRIS and Shared Services departments."
            ],
            "what can you do": [
                "I can help you with HR policies, leave requests, salary inquiries, and much more! Feel free to ask me anything. 😊",
                "As your virtual HR assistant, I can save you time by searching HSA Group policies, helping you submit leave requests, and checking your monthly salary slip — all without needing to visit HR in person! 👍",
                "I'm here to be your personal HR advisor at HSA Group. I can guide you through any administrative requirements, explain company policies, and even connect directly with SuccessFactors services like leave requests and salary slips in coordination with Shared Services and HRIS."
            ],
            "what is this system": [
                "I'm AskHRPro, the AI assistant for the HR and Shared Services department at HSA Group. How can I help you today? 😊",
                "Welcome! I'm your digital HR expert (AskHRPro) from the HRIS and Shared Services division at HSA Group. How can I assist you?",
                "I'm the HR expert for Hayel Saeed Anam Group (HSA Group). My role is to provide information and assistance regarding work policies, regulations, and employee-related procedures in coordination with Shared Services and HRIS. How can I help you today? 😊"
            ],
            "how can you help me": [
                "I can help you with HR policies, leave requests, salary inquiries, and much more! Feel free to ask me anything. 😊",
                "As your virtual HR assistant, I can save you time by searching HSA Group policies, helping you submit leave requests, and checking your monthly salary slip — all without needing to visit HR in person! 👍",
                "I'm here to be your personal HR advisor at HSA Group. I can guide you through any administrative requirements, explain company policies, and even connect directly with SuccessFactors services like leave requests and salary slips in coordination with Shared Services and HRIS."
            ],

            # Thanks & Appreciation
            "thank you": [
                "You're welcome! I'm always happy to help. 😊",
                "My pleasure! Have a wonderful day! 👍",
                "Anytime! If you have more questions, don't hesitate to ask."
            ],
            "thanks": [
                "You're welcome! I'm always happy to help. 😊",
                "My pleasure! Have a wonderful day! 👍",
                "Anytime! If you have more questions, don't hesitate to ask."
            ],
            "thanks a lot": [
                "You're very welcome! I'm always here to help. 😊",
                "Glad I could help! Have a great day! 👍"
            ],
            "thank you so much": [
                "You're very welcome! It's my pleasure to assist. 😊",
                "Glad I could help! Don't hesitate to reach out if you need anything else. 👍"
            ],
            "thank you very much": [
                "You're very welcome! It's my pleasure to assist. 😊",
                "Glad I could help! Don't hesitate to reach out if you need anything else. 👍"
            ],
            "thankful": [
                "You're welcome! Happy to help. 😊",
                "Glad I could assist! Let me know if you need anything else."
            ],
            "thx": [
                "You're welcome! Happy to help. 😊",
                "Glad I could assist! Let me know if you need anything else."
            ],
            "thnk u": [
                "You're welcome! Happy to help. 😊",
                "Glad I could assist! Let me know if you need anything else."
            ],
            "appreciate it": [
                "You're welcome! Happy to help. 😊",
                "Glad I could assist! Let me know if you need anything else."
            ],
            "much appreciated": [
                "You're welcome! I'm always happy to help. 😊",
                "My pleasure! Don't hesitate to reach out anytime."
            ],

            # Holiday & Seasonal greetings
            "happy new year": [
                "Happy New Year to you too! Wishing you a year full of success and happiness. 🎉 How can I help you today?",
                "Happy New Year! May this year bring you prosperity and joy. How can I assist you? 🎊"
            ],
            
            "jummah mubarak": [
                "Jummah Mubarak to you too! Wishing you a blessed and peaceful day. ✨ How can I help you today?",
                "Jummah Mubarak! May this day bring you peace and blessings. How can I assist you? 🤲"
            ],
            "happy holidays": [
                "Happy holidays to you too! Wishing you a wonderful time. 🎉 How can I help you today?",
                "Happy holidays! Hope you're enjoying the season. How can I assist you? 😊"
            ],
            "happy eid": [
                "Happy Eid to you too! May it be filled with blessings and joy. 🌸 How can I help you today?",
                "Eid Mubarak! Wishing you and your family a blessed celebration. How can I assist you? 😊"
            ],
            "eid mubarak": [
                "Eid Mubarak to you too! May this Eid bring you happiness and peace. 🌸 How can I help you today?",
                "Eid Mubarak! Wishing you and your loved ones a blessed and joyful Eid. How can I assist you? 😊"
            ],
            "ramadan mubarak": [
                "Ramadan Mubarak to you and your family! Wishing you a blessed and peaceful month. 🌙 How can I help you today?",
                "Ramadan Mubarak! May this holy month bring you peace, joy, and blessings. How can I assist you? ✨"
            ],
            "ramadan kareem": [
                "Ramadan Kareem! Wishing you a blessed and generous Ramadan. 🌙 How can I help you today?",
                "Ramadan Kareem! May this holy month be full of blessings for you and your family. How can I assist you? 😊"
            ],

            # Farewell / Goodbye
            "bye": [
                "Goodbye! Have a great day. Feel free to come back anytime! 👋",
                "Bye! Wishing you all the best. Don't hesitate to reach out if you need anything! 😊"
            ],
            "goodbye": [
                "Goodbye! It was great helping you. Have a wonderful day! 👋",
                "Goodbye! Feel free to come back anytime you need assistance. 😊"
            ],
            "see you": [
                "See you! Have a great day ahead! 👋",
                "See you later! Don't hesitate to come back anytime. 😊"
            ],
            "take care": [
                "You too! Take care and have a wonderful day! 😊",
                "Take care! I'm always here if you need help. 👋"
            ]
        }
        # Backward-compatible unified view (read-only convenience for tests)
        self.predefined_responses: Dict[str, List[str]] = {
            **self._arabic_responses,
            **self._english_responses
        }

    @staticmethod
    def _normalize_english(text: str) -> str:
        """
        Lightweight normalization for English text:
        - Lowercase
        - Strip punctuation and special characters
        - Collapse whitespace
        """
        text = text.lower()
        text = re.sub(r"[?!.,;:'\"\-_()\[\]{}/@#$%^&*~`]", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def _is_english(text: str) -> bool:
        """
        Heuristic language detection: Checks if the text contains Arabic characters.
        If no Arabic characters are present, or if ASCII letters dominate, 
        it treats the query as English/Generic to protect the pipeline.
        """
        if not text:
            return False

        # If it contains any Arabic character, check the letter distribution
        if re.search(r'[\u0600-\u06FF]', text):
            ascii_letters = sum(1 for c in text if c.isascii() and c.isalpha())
            total_letters = sum(1 for c in text if c.isalpha())
            if total_letters == 0:
                return False
            return (ascii_letters / total_letters) > 0.5
        
        # If there are no Arabic characters at all (only English letters, numbers, or symbols like '?')
        # default to True to trigger the English/Generic handling path.
        return True

    def match(self, query: str) -> Optional[str]:
        """
        Intercepts the user query. Detects the language first, then searches
        only in the language-specific dictionary with the appropriate normalizer.
        Returns a random matching response, or None if no match is found.
        """
        if not query:
            return None
        
        if self._is_english(query):
            # ── English path ──
            normalized = self._normalize_english(query)
            logger.debug(f"English normalized query: '{query}' -> '{normalized}'")
            responses = self._english_responses.get(normalized)
        else:
            # ── Arabic path ──
            normalized = normalize_arabic(query)
            logger.debug(f"Arabic normalized query: '{query}' -> '{normalized}'")
            responses = self._arabic_responses.get(normalized)

        if responses:
            chosen = random.choice(responses)
            logger.info(f"FastResponseFilter matched query: '{query}' with response: '{chosen}'")
            return chosen
            
        return None

