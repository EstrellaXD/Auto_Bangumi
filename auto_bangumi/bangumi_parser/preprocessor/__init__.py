from preprocessor.char_standardize import CharStandardize


class Preprocessor:
    def __init__(self) -> None:
        self._preprocessors = []
        self._preprocessors.append(CharStandardize())

    def preprocess(self, s: str) -> str:
        for preprocessor in self._preprocessors:
            s = preprocessor.preprocess(s)
        return s
