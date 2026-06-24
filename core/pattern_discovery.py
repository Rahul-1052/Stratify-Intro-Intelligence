    def test_descriptive_features_never_create_signals_or_position(self):
        result = self.discover()
        signals = result["missing_winning_features"] + result["risk_signals"]
        signal_features = {item["feature"] for item in signals}

        self.assertFalse(
            signal_features.intersection(
                {"brightness_level", "color_temperature"}
            )
        )
        self.assertTrue(
            all("brightness" not in item for item in result["user_position"])
        )
        self.assertTrue(
            all("color temperature" not in item for item in result["user_position"])
        )

    def test_risk_signal_creates_evidence_gated_recommendation(self):
        result = self.discover()
        risk_features = {item["feature"] for item in result["risk_signals"]}

        self.assertEqual(
            risk_features,
            {"human_presence", "motion_level", "scene_change_level"},
        )
        self.assertEqual(len(result["recommendations"]), 3)
        for recommendation in result["recommendations"]:
            self.assertEqual(
                set(recommendation),
                {
                    "title",
                    "evidence",
                    "why_it_matters",
                    "suggested_test",
                    "confidence",
                },
            )
            self.assertTrue(
                recommendation["suggested_test"].startswith(
                    ("Test", "Try", "Experiment with")
                )
            )
            self.assertIn(
                "does not establish cause",
                recommendation["why_it_matters"],
            )

    def test_same_group_dominants_create_no_recommendation(self):
        top = [benchmark(self.top_summary) for _ in range(3)]
        result = self.discover(top=top, lower=top)
        self.assertEqual(result["recommendations"], [])

    def test_unknown_user_value_has_insufficient_evidence(self):
        user = dict(self.user_summary)
        user["human_presence"] = "unknown"
        result = self.discover(user=user)
        comparison = next(
            item
            for item in result["feature_comparison"]
            if item["feature"] == "human_presence"
        )
        self.assertEqual(comparison["status"], "insufficient_evidence")

    def test_failed_rows_do_not_inflate_confidence(self):
        failed = [{"status": "failed"} for _ in range(3)]
        result = self.discover(top=failed)
        self.assertEqual(result["confidence"], "low")


if __name__ == "__main__":
    unittest.main()
