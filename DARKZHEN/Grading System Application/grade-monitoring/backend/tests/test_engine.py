from decimal import Decimal

from django.test import TestCase

from grading import engine


class EngineComputationTests(TestCase):
    def test_worked_example_from_architecture_document(self):
        sums = {
            engine.WW: (Decimal(78), Decimal(100)),
            engine.PT: (Decimal(85), Decimal(100)),
            engine.QA: (Decimal(42), Decimal(50)),
        }
        weights = {"WW": "25", "PT": "45", "QA": "30"}
        initial = engine.initial_grade(sums, weights)
        self.assertEqual(initial, Decimal("82.95"))
        self.assertEqual(engine.transmute(initial, engine.DEPED_TRANSMUTATION_TABLE), 89)

    def test_percentage_scores(self):
        self.assertEqual(engine.percentage_score(78, 100), Decimal(78))
        self.assertEqual(engine.percentage_score(42, 50), Decimal(84))
        self.assertIsNone(engine.percentage_score(5, 0))

    def test_weighted_scores(self):
        self.assertEqual(engine.weighted_score(Decimal(78), "25"), Decimal("19.5"))
        self.assertEqual(engine.weighted_score(Decimal(84), "30"), Decimal("25.2"))

    def test_semester_final_average(self):
        self.assertEqual(engine.semester_final([89, 91]), 90)

    def test_general_average_matches_document_example(self):
        self.assertEqual(engine.general_average([90, 88, 92, 89, 91]), 90)

    def test_quarterly_grade_with_no_scores_is_none(self):
        sums = {engine.WW: (Decimal(0), Decimal(0)), engine.PT: (Decimal(0), Decimal(0)), engine.QA: (Decimal(0), Decimal(0))}
        self.assertIsNone(engine.quarterly_grade(sums, {"WW": "25", "PT": "45", "QA": "30"}, engine.DEPED_TRANSMUTATION_TABLE))

    def test_blank_scores_excluded_but_zero_counts(self):
        sums = {
            engine.WW: (Decimal(0), Decimal(0)),
            engine.PT: (Decimal(0), Decimal(100)),
            engine.QA: (Decimal(0), Decimal(0)),
        }
        initial = engine.initial_grade(sums, {"WW": "25", "PT": "45", "QA": "30"})
        self.assertEqual(initial, Decimal(0))
        self.assertEqual(engine.transmute(initial, engine.DEPED_TRANSMUTATION_TABLE), 60)

    def test_incomplete_semester_returns_none(self):
        self.assertIsNone(engine.semester_final([89, None]))
        self.assertIsNone(engine.semester_final([None, 91]))

    def test_incomplete_general_average_returns_none(self):
        self.assertIsNone(engine.general_average([90, None, 92]))

    def test_transmutation_boundaries(self):
        table = engine.DEPED_TRANSMUTATION_TABLE
        self.assertEqual(engine.transmute(Decimal("100"), table), 100)
        self.assertEqual(engine.transmute(Decimal("84.00"), table), 90)
        self.assertEqual(engine.transmute(Decimal("83.99"), table), 89)
        self.assertEqual(engine.transmute(Decimal("82.40"), table), 89)
        self.assertEqual(engine.transmute(Decimal("60.00"), table), 75)
        self.assertEqual(engine.transmute(Decimal("59.99"), table), 74)
        self.assertEqual(engine.transmute(Decimal("6.00"), table), 60)
        self.assertEqual(engine.transmute(Decimal("5.99"), table), 60)

    def test_rounding_is_half_up(self):
        self.assertEqual(engine.semester_final([89, 90]), 90)
        self.assertEqual(engine.semester_final([88, 91]), 90)
        self.assertEqual(engine.general_average([90, 91]), 91)
        self.assertEqual(engine.general_average([90, 90, 91]), 90)

    def test_component_sums_from_scores_skips_blanks(self):
        items = [
            (engine.WW, None, Decimal(50)),
            (engine.WW, Decimal(30), Decimal(50)),
            (engine.PT, Decimal(10), Decimal(20)),
            (engine.QA, None, None),
        ]
        sums = engine.component_sums_from_scores(items)
        self.assertEqual(sums[engine.WW], (Decimal(30), Decimal(50)))
        self.assertEqual(sums[engine.PT], (Decimal(10), Decimal(20)))
        self.assertEqual(sums[engine.QA], (Decimal(0), Decimal(0)))


class QuarterTwoComputationTests(TestCase):
    def test_quarter_two_produces_91(self):
        sums = {
            engine.WW: (Decimal(84), Decimal(100)),
            engine.PT: (Decimal(86), Decimal(100)),
            engine.QA: (Decimal(44), Decimal(50)),
        }
        weights = {"WW": "25", "PT": "45", "QA": "30"}
        initial = engine.initial_grade(sums, weights)
        self.assertEqual(engine.transmute(initial, engine.DEPED_TRANSMUTATION_TABLE), 91)
