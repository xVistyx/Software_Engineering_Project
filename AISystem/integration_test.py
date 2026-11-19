import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from qwen_model import Qwen3Model

CONFIG = ROOT / "model_config_local.json" # on the GPU use model_config.json
ADAPTER = ROOT / "outputs" /"qwen3_4b_lora" #LoRA adapter


class TestPipeline(unittest.TestCase):
    def test_goal_and_page_go_through_the_whole_pipeline(self):
        model = Qwen3Model(str(CONFIG))
        model.config["model"]["adapter_path"] = str(ADAPTER)
        model.load()                                # loads the real Qwen3-4B and the adapter

        goal = "learn contract law"
        study_page = {"title": "Contract law - Wikipedia", "description": "Overview of contract law."}
        distraction = {"title": "Funny cat videos - YouTube", "description": "Watch the funniest cats."}

        study = model.classify_scored(goal, study_page)
        blocked = model.classify_scored(goal, distraction)

        self.assertIs(study["relevant"], True)          # study page is allowed
        self.assertIs(blocked["relevant"], False)       # distraction is blocked
        self.assertGreater(study["p_relevant"], blocked["p_relevant"])
        """
        Integration test of the whole flow in one go with the real model: study goal and page data go
        through preprocess, prompt building, the Qwen3-4B with the LoRA adapter, probability scoring and the
        decision rule. A clear study page must be allowed and a clear distraction blocked.
        """


if __name__ == "__main__":
    unittest.main()