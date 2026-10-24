import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from backend.routes.agent import ChatIn, chat as agent_chat
from backend.services import chat_service
from backend.services import planner_service


class TrainedIntentTests(unittest.TestCase):
    def test_model_predicts_all_supported_intents(self):
        examples = {
            "Tìm khách sạn có hồ bơi gần biển Mỹ Khê": "accommodation",
            "Tôi muốn tham quan những địa điểm nổi tiếng": "attraction",
            "Tìm quán cà phê yên tĩnh để học bài": "cafe",
            "Tôi muốn ăn mì Quảng ngon ở Đà Nẵng": "food",
            "Lập lịch trình du lịch Đà Nẵng hai ngày": "itinerary",
            "Viết cho tôi một đoạn code Python": "out_of_scope",
            "Đi từ sân bay đến cầu Rồng như thế nào?": "transport",
            "Ngày mai Đà Nẵng có mưa không?": "weather",
        }

        for message, expected in examples.items():
            with self.subTest(intent=expected):
                intent, confidence = chat_service.predict_intent(message)
                self.assertEqual(intent, expected)
                self.assertGreater(confidence, 0)

    @patch("backend.services.chat_service.planner.build_itinerary")
    @patch(
        "backend.services.chat_service.predict_intent",
        return_value=("weather", 0.99),
    )
    def test_itinerary_keywords_override_model_prediction(
        self,
        predict_intent,
        build_itinerary,
    ):
        build_itinerary.return_value = "Lịch trình kiểm thử"

        result = chat_service.answer(
            "Lập lịch trình du lịch Đà Nẵng một ngày",
            db=None,
            lat=16.05,
            lng=108.20,
        )

        self.assertEqual(result["intent"], "itinerary")
        self.assertEqual(result["reply"], "Lịch trình kiểm thử")
        build_itinerary.assert_called_once_with(
            None,
            "Lập lịch trình du lịch Đà Nẵng một ngày",
            True,
            16.05,
            108.20,
        )
        predict_intent.assert_called_once()

    @patch("backend.services.chat_service.planner.fetch_weather", return_value=None)
    @patch(
        "backend.services.chat_service.predict_intent",
        return_value=("itinerary", 0.9),
    )
    def test_itinerary_uses_places_without_coordinates(
        self,
        predict_intent,
        fetch_weather,
    ):
        places = [
            SimpleNamespace(
                id=1,
                name="Quán ăn sáng địa phương",
                category="restaurant",
                address="Đà Nẵng",
                description="Món ăn sáng",
                opening_hours=None,
                latitude=None,
                longitude=None,
                rating=None,
            ),
            SimpleNamespace(
                id=2,
                name="Bảo tàng Điêu khắc Chăm",
                category="tourist_attraction",
                address="Đà Nẵng",
                description="Bảo tàng văn hóa Chăm",
                opening_hours=None,
                latitude=None,
                longitude=None,
                rating=None,
            ),
            SimpleNamespace(
                id=3,
                name="Nhà hàng địa phương",
                category="restaurant",
                address="Đà Nẵng",
                description="Ẩm thực địa phương",
                opening_hours=None,
                latitude=None,
                longitude=None,
                rating=None,
            ),
            SimpleNamespace(
                id=4,
                name="Điểm tham quan thiên nhiên",
                category="tourist_attraction",
                address="Đà Nẵng",
                description="Cảnh quan thiên nhiên",
                opening_hours=None,
                latitude=None,
                longitude=None,
                rating=None,
            ),
        ]
        db = Mock()
        db.query.return_value.filter.return_value.all.return_value = places

        result = chat_service.answer(
            "Lập lịch trình du lịch Đà Nẵng một ngày",
            db,
        )

        self.assertEqual(result["intent"], "itinerary")
        self.assertIn("Ăn sáng", result["reply"])
        self.assertIn("Tham quan văn hóa", result["reply"])
        self.assertIn("Chưa có tọa độ", result["reply"])
        predict_intent.assert_called_once()
        fetch_weather.assert_called_once()

    @patch("backend.routes.agent.answer", return_value={"reply": "ok"})
    def test_chat_route_forwards_both_gps_coordinates(self, answer):
        payload = ChatIn(
            message="Find places near me",
            latitude=16.05,
            longitude=108.20,
        )
        db = object()

        agent_chat(payload, db)

        answer.assert_called_once_with(
            "Find places near me",
            db,
            16.05,
            108.20,
        )

    def test_nearby_explains_when_database_has_no_coordinates(self):
        place = SimpleNamespace(latitude=None, longitude=None)
        db = Mock()
        db.query.return_value.filter.return_value.all.return_value = [place]

        reply = planner_service.nearby(
            db,
            "restaurant",
            16.05,
            108.20,
        )

        self.assertIn("Chưa có tọa độ", reply)


if __name__ == "__main__":
    unittest.main()
