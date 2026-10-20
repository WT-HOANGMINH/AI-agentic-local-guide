
import os

from dotenv import load_dotenv
from google import genai

# Doc cau hinh tu file .env o thu muc goc du an
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

_client = None


def get_gemini_client():
    """Tao client khi can, tranh khoi tao neu chua co API key."""
    global _client

    if not GEMINI_API_KEY:
        raise RuntimeError(
            "Chua cau hinh GEMINI_API_KEY trong file .env"
        )

    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)

    return _client


def ask_llm(question: str) -> str:
    """Gui cau hoi den Gemini va tra ve cau tra loi."""
    question = question.strip()

    if not question:
        raise ValueError("Cau hoi khong duoc de trong.")

    client = get_gemini_client()

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=(
            "Ban la tro ly AI du lich Da Nang. "
            "Tra loi bang tieng Viet, ro rang va huu ich. "
            "Khong tu khang dinh dia diem, gia ca hoac gio mo cua "
            "la chinh xac neu chua co du lieu xac minh.\n\n"
            f"Cau hoi cua nguoi dung: {question}"
        ),
    )

    answer = response.text

    if not answer:
        raise RuntimeError("LLM khong tra ve noi dung.")

    return answer.strip()
