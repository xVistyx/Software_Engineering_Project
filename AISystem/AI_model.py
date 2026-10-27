from abc import abstractmethod, ABC
from preprocess import preprocess

class Model(ABC):
    def __init__(self, config):
        self.config = config
        self.model = None
        self.tokenizer = None


    @abstractmethod
    def load(self):
        pass

    @abstractmethod
    def tokenise(self, prompt_text):
        pass

    @abstractmethod
    def generate(self, inputs):
        pass


    def build_prompt(self, query, page_data):
        prompt = (
            f"Study session goal: {query}\n\n"
            f"{preprocess(page_data)}\n\n"
            "Is this page relevant to the study session goal? "
            'Answer with just JSON: {"relevant": true or false}'
        )
        return prompt
    
    def classify(self, query, page_data):
        prompt = self.build_prompt(query, page_data)

    def parse(self, raw_text):
        pass

    def train(self, dataset):
        pass

    def save_adapter(self, path):
        pass

    def load_adapter(self, path):
        pass

    def evaluate(self, dataset):
        pass
        #calls classify






    