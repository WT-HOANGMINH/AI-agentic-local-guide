
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

sys.stdout.reconfigure(encoding="utf-8")

from backend.services.intent_service import predict_intent

# Cac cau noi thu nghiem moi
test_sentences = [
    "Tôi muốn ăn món đặc sản Đà Nẵng",
    "Đà Nẵng có địa điểm du lịch nào nổi tiếng?",
    "Tìm cho tôi một quán cà phê yên tĩnh",
    "Lập lịch trình du lịch Đà Nẵng trong 2 ngày",
    "Tôi nên đi đến Bà Nà Hills bằng phương tiện gì?",
]

# Du doan y dinh cua tung cau
for sentence in test_sentences:
    result = predict_intent(sentence)

    print(f"\nCau hoi: {sentence}")
    print(f"Y dinh du doan: {result['intent']}")
    print(f"Do tin cay tham khao: {result['confidence']:.2%}")
