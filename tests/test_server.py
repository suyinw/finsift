import unittest
from unittest.mock import patch

from server import (
    MOCK_ARTICLES,
    apply_scorecard_policy,
    build_state,
    call_laya,
    call_strands_decider,
    jev_questions,
    mock_jev,
    validate_company,
    validate_model_selection,
)


class NewsScorecardTests(unittest.TestCase):
    def test_jev_questions_use_all_primitives(self):
        self.assertEqual(
            {question["type"] for question in jev_questions().values()},
            {"choice", "score", "noul"},
        )
        self.assertEqual(len(jev_questions()), 5)

    def test_state_contains_textual_article_metadata(self):
        state = build_state("Northstar Cloud", "NSTR", MOCK_ARTICLES)
        self.assertEqual(state["article_count"], len(MOCK_ARTICLES))
        self.assertIn("headline", state["articles"][0])
        self.assertNotIn("url", state["articles"][0])

    def test_mock_produces_valid_scorecard(self):
        result = apply_scorecard_policy(mock_jev(MOCK_ARTICLES), len(MOCK_ARTICLES))
        self.assertGreaterEqual(result["scorecard"]["score"], 0)
        self.assertLessEqual(result["scorecard"]["score"], 100)
        self.assertNotIn("confidence", result["scorecard"])
        self.assertIn(
            result["scorecard"]["posture_code"],
            {"candidate", "watch", "low", "insufficient"},
        )

    def test_thin_coverage_is_not_actionable(self):
        result = apply_scorecard_policy(mock_jev(MOCK_ARTICLES[:1]), 1)
        self.assertEqual(result["scorecard"]["posture_code"], "insufficient")

    def test_company_validation(self):
        self.assertEqual(
            validate_company({"company": "Amazon.com", "ticker": "amzn"}),
            ("Amazon.com", "AMZN"),
        )
        with self.assertRaises(ValueError):
            validate_company({"company": "A", "ticker": "bad ticker"})

    def test_model_selection_validation(self):
        self.assertEqual(validate_model_selection({}), "all")
        self.assertEqual(
            validate_model_selection({"model_selection": "STRANDS"}),
            "strands",
        )
        self.assertEqual(
            validate_model_selection({"model_selection": "laya"}),
            "laya",
        )
        with self.assertRaises(ValueError):
            validate_model_selection({"model_selection": "unknown"})

    @patch("server.urlopen")
    def test_strands_adapter_uses_system_one_contract(self, mock_urlopen):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return b"""{
                    "model": "strands-decider-test",
                    "answers": {},
                    "usage": {"input_tokens": 10, "output_tokens": 5}
                }"""

        mock_urlopen.return_value = Response()
        state = build_state("Northstar Cloud", "NSTR", MOCK_ARTICLES)
        result = call_strands_decider(state)
        request = mock_urlopen.call_args.args[0]
        self.assertTrue(request.full_url.endswith("/v1/systemone"))
        self.assertIn(b'"business_momentum"', request.data)
        self.assertEqual(result["provider"], "Local Strands Decider")

    @patch("server.urlopen")
    def test_laya_adapter_uses_system_one_contract(self, mock_urlopen):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return b"""{
                    "model": "typed-decisions",
                    "answers": {},
                    "usage": {"input_tokens": 10, "output_tokens": 5}
                }"""

        mock_urlopen.return_value = Response()
        state = build_state("Northstar Cloud", "NSTR", MOCK_ARTICLES)
        result = call_laya(state)
        request = mock_urlopen.call_args.args[0]
        self.assertTrue(request.full_url.endswith("/v1/systemone"))
        self.assertIn(b'"model": "typed-decisions"', request.data)
        self.assertIn(b'"business_momentum"', request.data)
        self.assertEqual(result["provider"], "Local Laya")


if __name__ == "__main__":
    unittest.main()
