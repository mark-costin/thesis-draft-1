"""
FHRS engine (backend/cdss/fhrs.py): the CDSS FHRS Guide formula, constants from cdss_spec.json.

  BioFHRS_d      = sum(R_i * O_i * S_i) + C_d
  AdjustedFHRS_d = BioFHRS_d * E_d,  E_d = 1.0 + sum(e_j)
  Band from the adjusted score: 0 | (0, 1.76) | [1.76, 3.51) | [3.51, 6.00] | > 6.00
"""
import json
import unittest

from tests._helpers import ROOT

EXPERIMENT_SPEC = ROOT / "experiment" / "data" / "reference" / "cdss_spec.json"
BACKEND_SPEC = ROOT / "backend" / "cdss" / "cdss_spec.json"


def rel(tier, onset, verified):
    from backend.cdss.fhrs import Relative
    return Relative(tier=tier, onset=onset, verified=verified)


class DictionaryExampleTests(unittest.TestCase):
    """CDSS_Data_Dictionary.pdf, FHRS Guide section 6: 'Meet John'."""

    def setUp(self):
        from backend.cdss.fhrs import compute
        self.result = compute("cvd", [
            rel(1, "early", True),          # father, heart attack at 48, proven: 0.5 x 2.0 x 1.0
            rel(1, "severe_early", True),   # brother, stent at 38, proven:       0.5 x 3.0 x 1.0
            rel(2, "typical", False),       # uncle, at 60, memory only:          0.25 x 1.0 x 0.5
        ], ["secondhand_smoke"])            # + 0.15

    def test_pedigree_terms_add_up_to_2_625(self):
        self.assertAlmostEqual(self.result["pedigree_sum"], 2.625)

    def test_two_verified_immediate_relatives_add_the_1_0_cluster_bonus(self):
        self.assertAlmostEqual(self.result["clustering"], 1.0)

    def test_biological_score_is_3_625(self):
        self.assertAlmostEqual(self.result["bio_fhrs"], 3.625)

    def test_environmental_modifier_is_1_15(self):
        self.assertAlmostEqual(self.result["environmental_modifier"], 1.15)

    def test_final_score_is_4_17_band_3_pronounced(self):
        self.assertAlmostEqual(self.result["adjusted_fhrs"], 4.16875)
        self.assertEqual(round(self.result["adjusted_fhrs"], 2), 4.17)
        self.assertEqual(self.result["band"], 3)
        self.assertEqual(self.result["band_label"], "Pronounced Risk")


class FormulaTests(unittest.TestCase):
    def compute(self, disease, relatives, hazards=()):
        from backend.cdss.fhrs import compute
        return compute(disease, relatives, list(hazards))

    def test_no_relatives_is_band_0_even_with_hazards(self):
        r = self.compute("cvd", [], ["secondhand_smoke"])
        self.assertEqual(r["adjusted_fhrs"], 0.0)
        self.assertEqual(r["band"], 0)
        self.assertEqual(r["band_label"], "Baseline Risk")

    def test_kinship_by_tier(self):
        for tier, expected in ((1, 0.5), (2, 0.25), (3, 0.125)):
            self.assertAlmostEqual(self.compute("t2d", [rel(tier, "typical", True)])["bio_fhrs"], expected)

    def test_onset_multipliers(self):
        for onset, expected in (("severe_early", 1.5), ("early", 1.0), ("typical", 0.5), ("late", 0.375)):
            self.assertAlmostEqual(self.compute("t2d", [rel(1, onset, True)])["bio_fhrs"], expected)

    def test_unverified_relative_counts_half(self):
        self.assertAlmostEqual(self.compute("t2d", [rel(1, "typical", False)])["bio_fhrs"], 0.25)

    def test_unverified_relatives_never_form_a_cluster(self):
        r = self.compute("cvd", [rel(1, "typical", False), rel(1, "typical", False)])
        self.assertEqual(r["clustering"], 0.0)

    def test_cluster_weight_by_tier(self):
        # W_k * max(0, verified_k - 1): tier 2 weight 0.5, tier 3 weight 0.25
        self.assertAlmostEqual(self.compute("cvd", [rel(2, "typical", True)] * 3)["clustering"], 1.0)
        self.assertAlmostEqual(self.compute("cvd", [rel(3, "typical", True)] * 2)["clustering"], 0.25)

    def test_band_edges(self):
        from backend.cdss.fhrs import assign_band
        cases = {0.0: 0, 0.05: 1, 1.75: 1, 1.76: 2, 3.50: 2, 3.51: 3, 6.00: 3, 6.01: 4}
        for score, band in cases.items():
            self.assertEqual(assign_band(score), band, score)

    def test_each_hazard_counts_once(self):
        r = self.compute("resp", [rel(1, "typical", True)], ["biomass_heating", "biomass_heating"])
        self.assertAlmostEqual(r["environmental_modifier"], 1.35)

    def test_hazards_add_up(self):
        r = self.compute("t2d", [rel(1, "typical", True)], ["processed_diet", "physical_inactivity"])
        self.assertAlmostEqual(r["environmental_modifier"], 1.35)

    def test_hazard_from_another_disease_is_rejected(self):
        from backend.cdss.fhrs import FhrsError
        with self.assertRaises(FhrsError):
            self.compute("cvd", [], ["biomass_heating"])

    def test_neuro_has_no_hazards_until_sourced(self):
        from backend.cdss.fhrs import HAZARDS
        self.assertEqual(HAZARDS["neuro"], {})

    def test_bad_tier_or_onset_is_rejected(self):
        from backend.cdss.fhrs import FhrsError
        with self.assertRaises(FhrsError):
            self.compute("cvd", [rel(4, "typical", True)])
        with self.assertRaises(FhrsError):
            self.compute("cvd", [rel(1, "sudden", True)])


class HazardListTests(unittest.TestCase):
    """The agreed list (2026-10-15): values from Harrison's / the dictionary, pending physician sign-off."""

    def test_agreed_values(self):
        from backend.cdss.fhrs import HAZARDS
        values = {d: {code: h["e_j"] for code, h in hazards.items()} for d, hazards in HAZARDS.items()}
        self.assertEqual(values, {
            "cvd": {"secondhand_smoke": 0.15, "high_salt_diet": 0.10},
            "t2d": {"processed_diet": 0.15, "physical_inactivity": 0.20},
            "resp": {"indoor_allergens": 0.10, "biomass_heating": 0.35, "secondhand_smoke": 0.15},
            "neuro": {},
        })

    def test_every_value_is_inside_the_project_range_and_has_a_source(self):
        from backend.cdss.fhrs import HAZARD_RANGE, HAZARDS
        low, high = HAZARD_RANGE
        for disease, hazards in HAZARDS.items():
            for code, h in hazards.items():
                self.assertTrue(low <= h["e_j"] <= high, f"{disease}.{code}")
                self.assertTrue(h["label"] and h["source"] and h["status"], f"{disease}.{code}")


class SpecFileTests(unittest.TestCase):
    def test_constants_come_from_the_spec_file(self):
        from backend.cdss import fhrs
        spec = json.loads(BACKEND_SPEC.read_text(encoding="utf-8"))["fhrs"]
        self.assertEqual(fhrs.TIER_KINSHIP, {int(k): v for k, v in spec["kinship_by_tier"].items()})
        self.assertEqual(fhrs.BAND_EDGES, spec["band_edges"])

    @unittest.skipUnless(EXPERIMENT_SPEC.exists(), "experiment/data/reference/cdss_spec.json not present")
    def test_backend_copy_matches_the_generator_spec(self):
        # One set of numbers for training data and the live backend.
        self.assertEqual(json.loads(BACKEND_SPEC.read_text(encoding="utf-8")),
                         json.loads(EXPERIMENT_SPEC.read_text(encoding="utf-8")))


class MigrationTests(unittest.TestCase):
    """database/migrations/2026-10-15_fhrs_part2.sql brings the live tables in line with the models."""

    def setUp(self):
        self.sql = (ROOT / "database" / "migrations" / "2026-10-15_fhrs_part2.sql").read_text(encoding="utf-8")

    def test_adds_the_verified_flag_unverified_by_default(self):
        self.assertIn("ALTER TABLE patient_family_history ADD COLUMN IF NOT EXISTS is_verified boolean NOT NULL DEFAULT false;", self.sql)

    def test_adds_biological_sex_with_the_dictionary_values(self):
        self.assertIn("ALTER TABLE patients ADD COLUMN IF NOT EXISTS biological_sex varchar(10);", self.sql)
        self.assertIn("CHECK (biological_sex IN ('Female', 'Male'))", self.sql)

    def test_creates_the_hazard_table_with_one_row_per_hazard(self):
        self.assertIn("CREATE TABLE IF NOT EXISTS patient_environmental_hazards", self.sql)
        self.assertIn("UNIQUE (patient_id, disease_domain, hazard_code)", self.sql)

    def test_runs_in_one_transaction(self):
        self.assertIn("BEGIN;", self.sql)
        self.assertTrue(self.sql.rstrip().endswith("COMMIT;"))


if __name__ == "__main__":
    unittest.main()
