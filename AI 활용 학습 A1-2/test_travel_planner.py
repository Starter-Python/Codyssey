"""travel_planner.py의 외부 API 호출 없이 검증 가능한 핵심 동작 테스트."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# requests 또는 dotenv가 설치되지 않은 환경에서도 단위 테스트가 독립적으로 실행될 수 있도록 모의 객체 주입
for mod_name in ("requests", "dotenv"):
    if mod_name not in sys.modules:
        try:
            __import__(mod_name)
        except ImportError:
            sys.modules[mod_name] = MagicMock()

import travel_planner as planner


class TravelPlannerTest(unittest.TestCase):
    def test_valid_recommendation_is_accepted(self):
        data = {
            "recommended_city": "제주",
            "weather": "온화하고 바람이 있습니다.",
            "events": ["봄 행사 후보"],
            "reason": "야외 활동에 적합합니다. 계절 풍경을 즐길 수 있습니다.",
        }
        self.assertEqual(planner.validate_recommendation(data), data)

    def test_recommendation_missing_required_key_is_rejected(self):
        invalid = {"recommended_city": "제주", "weather": "맑음", "events": []}
        with self.assertRaises(ValueError):
            planner.validate_recommendation(invalid)

    def test_kakao_place_is_normalized(self):
        raw = {
            "place_name": "테스트 식당",
            "road_address_name": "제주특별자치도 제주시 테스트로 1",
            "category_name": "음식점 > 한식",
            "place_url": "https://place.map.kakao.com/1",
            "x": "126.5312",
            "y": "33.4996",
        }
        result = planner.normalize_place(raw)
        self.assertEqual(result["name"], "테스트 식당")
        self.assertEqual(result["address"], "제주특별자치도 제주시 테스트로 1")
        self.assertIsInstance(result["x"], float)
        self.assertIsInstance(result["y"], float)

    def test_normalize_city_name(self):
        # 광역 지자체 및 특별자치도 보정 검증
        self.assertEqual(planner.normalize_city_name("강원도"), "강릉")
        self.assertEqual(planner.normalize_city_name("제주특별자치도"), "제주")
        self.assertEqual(planner.normalize_city_name("경주"), "경주")

    def test_extract_json_object_with_markdown_fence(self):
        # 마크다운 코드블록 및 앞뒤 문구가 붙어도 JSON 추출
        raw = "여기 추천 결과입니다:\n```json\n{\"recommended_city\": \"여수\"}\n```\n좋은 여행 되세요!"
        extracted = planner.extract_json_object(raw)
        self.assertEqual(extracted, '{"recommended_city": "여수"}')

    def test_missing_kakao_key_keeps_pipeline_alive(self):
        errors = []
        with patch.dict(os.environ, {"KAKAO_REST_API_KEY": ""}, clear=False):
            places = planner.search_restaurants("제주", errors)
        self.assertEqual(places, [])
        self.assertEqual(errors[0]["type"], "MISSING_API_KEY")

    def test_fallback_report_marks_empty_restaurants(self):
        recommendation = {
            "recommended_city": "강릉",
            "weather": "선선합니다.",
            "events": ["문화행사 후보"],
            "reason": "바다와 도심을 함께 즐길 수 있습니다.",
        }
        report = planner.fallback_report("2026-10-03", recommendation, [], [])
        self.assertIn("## 맛집 추천", report)
        self.assertIn("데이터 없음", report)
        self.assertIn("## 1일 일정 제안", report)

    def test_invalid_date_exits_with_parser_error(self):
        with patch.object(sys, "argv", ["travel_planner.py", "--date", "2026-02-30"]):
            with self.assertRaises(SystemExit) as context:
                planner.parse_args()
        self.assertNotEqual(context.exception.code, 0)

    def test_load_cached_data_success(self):
        # 임시 디렉토리에 캐시 파일 생성 후 정상 로드 검증
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            sample = {
                "travel_date": "2026-10-03",
                "recommendation": {"recommended_city": "경주"},
                "restaurants": [{"name": "황남빵"}],
            }
            cache_file = tmppath / "2026-10-03_travel_data.json"
            cache_file.write_text(json.dumps(sample), encoding="utf-8")
            with patch.object(planner, "RESULTS_DIR", tmppath):
                loaded = planner.load_cached_data("2026-10-03")
                self.assertIsNotNone(loaded)
                self.assertEqual(loaded["recommendation"]["recommended_city"], "경주")


if __name__ == "__main__":
    unittest.main()
