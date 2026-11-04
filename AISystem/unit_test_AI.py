import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent)) 
from AI_model import Model

CONFIG = {"default_model": "fake", "models": {"fake": {
    "lora": {}, "training": {}, "tokenizer": {"chat_template_kwargs": {}},
    "decision": {"relevance_threshold": 0.5, "uncertain_band": 0.15, "min_answer_mass": 0.5},
}}}
PAGE = {"title": "Contract law - Wikipedia", "description": "Overview of contract law."}

class FakeModel(Model):
    def __init__(self, config_path, p=0.9, mass=1.0):
        super().__init__(config_path)
        self.p, self.mass = p, mass

    def load(self): 
        pass

    def tokenise(self, prompt_text): 
        return prompt_text
    
    def generate(self, inputs): 
        return ""
    
    def score(self, prompt_text):
        return {"p_relevant": self.p, "logit_margin": 0.0, "answer_mass": self.mass}


class ModelTestCase(unittest.TestCase):
    def make(self, **kwargs):
        tmp = tempfile.TemporaryDirectory() #throwaway config file
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "config.json"
        path.write_text(json.dumps(CONFIG))
        return FakeModel(str(path), **kwargs)


class TestParseOutput(ModelTestCase):
    def test_valid_output_is_read_correctly(self):
        cases = {
            '{"relevant": true}': True,
            '{"relevant": false}': False,
            '{ "relevant" :   FALSE }': False,                      # spacing and capitals
            '```json\n{"relevant": false}\n```': False,             # code fence around it
            'Sure! {"relevant": false} Hope that helps.': False,    # text around it
            '{"relevant": "false"}': False,                         # boolean written as a string
        }
        model = self.make()
        for raw, expected in cases.items():
            with self.subTest(raw=raw): #failure is recorded and test goes on
                self.assertIs(model.parse(raw), expected) #asserts the result as expected
        """
        Unit test for if parsing has occurred correctly, checks output parser, `Model.parse()` 
        for if model's JSON answer has been returned in a correct format. This test include 
        different spacing and capitalisation, text around the JSON, and a boolean 
        written as a string. This test goes through a table of example of outputs and their 
        expected result, and assert that parse() returned exactly that boolean for each.
        """

    def test_unreadable_output_is_treated_as_relevant(self):
        """Wrong format must never block a page: unparseable output means 'relevant'."""
        model = self.make()
        for raw in ["", "yes", "{}", '{"relevant": maybe}', '{"answer": false}', None, 123, ["relevant"]]:
            with self.subTest(raw=raw):
                self.assertIs(model.parse(raw), True)
        """
        This verifies the failure case. WHen the output is garbage, empty or no text at all,
        parse() should return True (relevant), so that a format error never causes a study page
        to be blocked.
        """


class TestDecisionRule(ModelTestCase):
    def test_probability_into_block_or_allow(self):
        cases = [                    # (p_relevant, relevant, uncertain)
            (0.99, True, False),     # sure it is relevant -> allow
            (0.01, False, False),    # sure it is a distraction -> block
            (0.30, False, False),    # low probability -> block
            (0.45, False, True),     # block, but close to the line 
            (0.55, True, True),      # allow, but close to the line
            (0.50, True, True),      # exactly on the threshold counts as relevant: do not block
            (0.65, True, False),     # just outside the uncertain band
            (0.35, False, False),    # just outside the uncertain band
        ]
        for p, relevant, uncertain in cases:
            with self.subTest(p=p):
                result = self.make(p=p).classify_scored("goal", PAGE)
                self.assertIs(result["relevant"], relevant)
                self.assertIs(result["uncertain"], uncertain)
        """
        This test ives the classifier a list of fixed probabilities, from clearly relevant to clearly
        irrelevant and including values on the boundaries.
        For each one it checks that the decision is correct where
        low probability is blocked and a high one is allowed and probabilities close to 0.5
        are flagged as uncertain. A fake model provides the probability. 
        """
 
    def test_threshold_and_band_come_from_the_config(self):
        result = self.make(decision={"relevance_threshold": 0.8, "uncertain_band": 0.05}, p=0.7).classify_scored("goal", PAGE)
        self.assertIs(result["relevant"], False)
        self.assertIs(result["uncertain"], False)    
        """
        This test changes the threshold and the uncertainty band in the configuration and 
        checks that the decision changes with them. A probability that would normally be allowed is
        now blocked. This shows that the values are read from the configuration and the decision
        is modified accordingly. 
        """  


class TestResultFormat(ModelTestCase):
    def test_result_has_the_expected_keys_and_types(self):
        result = self.make(p=0.3).classify_scored("learn contract law", PAGE)
        for key in ("relevant", "p_relevant", "uncertain", "reason"):
            self.assertIn(key, result)
        self.assertIsInstance(result["relevant"], bool)
        self.assertIsInstance(result["uncertain"], bool)
        self.assertIsInstance(result["p_relevant"], float)
        self.assertIsInstance(result["reason"], str)
        """
        This unit test checks the output format of the classify_scored() function. 
        For a noraml input, the result must contain `relevant`, `p_relevant`,
        `uncertain` and `reason`. It is important that this format is guaranteed such that
        the backend and the extension always receive a result in the same format, thus, can 
        physically block or not block the website. 
        """

    def test_probability_stays_between_0_and_1(self):
        for p in (0.0, 0.25, 0.5, 1.0):
            with self.subTest(p=p):
                result = self.make(p=p).classify_scored("goal", PAGE)
                self.assertGreaterEqual(result["p_relevant"], 0.0)
                self.assertLessEqual(result["p_relevant"], 1.0)
        """
        This test verifies that the probability retuend to the caller is always within the valid range
        including the boundary values of 0 and 1. This is so that the interface will never return a 
        meaningless probability, which would prevent the model
        from being able to classify between block and not blocking. 
        """
        


class TestBrokenScore(ModelTestCase):
    def test_unusable_score_does_not_block(self):
        for p, mass in [(float("nan"), 1.0), (0.1, float("nan")), (None, 1.0), ("0.1", 1.0)]:
            with self.subTest(p=p, mass=mass):
                result = self.make(p=p, mass=mass).classify_scored("goal", PAGE)
                self.assertTrue(result["relevant"])
                self.assertTrue(result["uncertain"])
        """
        This unit test verifies the fail-safe behavior for corrupted score. If the probability or the 
        answer mass is not available, missing, or the wrong type,
        `classify_scored()` does not block the page and marks the result as
        uncertain. This prevents a numerical or format failure in the model from wrongly 
        blocking a study page. 
        """

    def test_model_that_did_not_answer_true_or_false_does_not_block(self):
        result = self.make(p=0.01, mass=0.2).classify_scored("goal", PAGE)   # very low p, but unreliable
        self.assertTrue(result["relevant"])
        self.assertTrue(result["uncertain"])
        """
        This teest verifies when the probability mass that the model assigns
        to the token `true` or `false` is below the configured minimum, the computed
        probability is considered unreliable, so the page is allowed but marked uncertain, even 
        if the result itself indicates a block. 

        """


if __name__ == "__main__":
    unittest.main()