
import os

from dotenv import load_dotenv
from google import genai

# Doc cau hinh tu file .env o thu muc goc du an
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

_client = None
_client_key = None


def is_gemini_configured():
    return bool(os.getenv("GEMINI_API_KEY") or GEMINI_API_KEY)


def get_gemini_client():
    """Tao client khi can, tranh khoi tao neu chua co API key."""
    global _client, _client_key

    api_key = os.getenv("GEMINI_API_KEY") or GEMINI_API_KEY
    if not api_key:
        raise RuntimeError(
            "Chua cau hinh GEMINI_API_KEY trong file .env"
        )

    if _client is None or _client_key != api_key:
        _client = genai.Client(api_key=api_key)
        _client_key = api_key

    return _client


def stream_grounded_answer(question: str, grounded_answer: str):
    """Stream user-facing text only; never forward Gemini thought events."""
    question = question.strip()
    grounded_answer = grounded_answer.strip()
    if not question or not grounded_answer:
        raise ValueError("Question and grounded answer are required.")

    client = get_gemini_client()
    stream = client.interactions.create(
        model=os.getenv("GEMINI_MODEL", GEMINI_MODEL),
        input=(
            f"Yêu cầu của khách: {question}\n\n"
            f"Thông tin đã được ứng dụng xác minh từ dữ liệu địa điểm: "
            f"{grounded_answer}"
        ),
        system_instruction=(
            "Bạn là DaNang Guide, một người bạn bản địa Đà Nẵng: nói tiếng Việt thân thiện, ấm áp, "
            "tự nhiên như đang trò chuyện, có thể dùng emoji vừa phải. "
            "Hãy viết lại câu trả lời dựa DUY NHẤT trên thông tin đã xác minh: giữ nguyên mọi tên địa điểm, "
            "giờ giấc, số liệu và thứ tự trong lịch trình; không bỏ sót mục nào; không thêm địa điểm, giá, "
            "giờ mở cửa, khoảng cách hay dữ kiện mới. Bạn được thêm một câu mở đầu thân thiện và tối đa "
            "một mẹo chung không chứa số liệu mới. Giữ định dạng danh sách/khung giờ để dễ đọc. "
            "Không viết lời chào kết hay lời chúc cuối (ứng dụng sẽ tự thêm). "
            "Không nhắc tên mô hình, cấu hình kỹ thuật hay suy nghĩ nội bộ."
        ),
        generation_config={
            "max_output_tokens": 3072,
            "thinking_level": "low",
        },
        stream=True,
    )

    output_indices = set()
    for event in stream:
        if event.event_type == "step.start":
            step = getattr(event, "step", None)
            if getattr(step, "type", None) == "model_output":
                output_indices.add(event.index)
        elif event.event_type == "step.delta" and event.index in output_indices:
            delta = event.delta
            if getattr(delta, "type", None) == "text" and delta.text:
                yield delta.text


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
