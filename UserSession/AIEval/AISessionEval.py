
from pathlib import Path
from AISystem.qwen_model import Qwen3Model


class AISessionEval:
    def __init__(self):
        """
        Initialize the AI evaluator and load the trained model.
        This happens only once when the class is instantiated.
        """

        base_dir = Path(__file__).resolve().parents[2] / "AISystem"

        # Load model configuration
        config_path = base_dir / "model_config_local.json"

        self.model = Qwen3Model(str(config_path))

        # Point to the trained LoRA adapter
        adapter_path = base_dir / "outputs" / "qwen3_4b_lora"

        self.model.config["model"]["adapter_path"] = str(adapter_path)

        # Load Qwen3-4B and its fine-tuned adapter
        self.model.load()

    def is_session_related(self, meta_data: dict, topic: str) -> bool:
        """
        Public interface used by other classes.

        Returns:
            True: Website is related to the study session.
            False: Website is unrelated to the study session.
        """

        return self.AI_meta_data_eval(meta_data, topic)

    def AI_meta_data_eval(self, meta_data: dict, topic: str) -> bool:
        """
        Run inference using the fine-tuned AI model.

        Args:
            meta_data: Website metadata containing title and description.
            topic: The current study session topic.

        Returns:
            Boolean indicating whether the website is relevant.
        """

        result = self.model.classify_scored(topic, meta_data)

        return bool(result["relevant"])
