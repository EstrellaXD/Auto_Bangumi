import logging

logger = logging.getLogger(__name__)

from preprocessor import Preprocessor
from token_generator import TokenGenerator
from analyser import Analyser


class Parser:
    def __init__(self) -> None:
        self._preprocessor = Preprocessor()
        self._token_generator = TokenGenerator()
        self._analyser = Analyser()

    def parse(self, name: str):
        name = self._preprocessor.preprocess(name)
        tokens = self._token_generator.generate(name)
        episode = self._analyser.analyse(name, tokens)
        return episode, tokens, name


if __name__ == "__main__":
    import sys, os

    sys.path.append(os.path.dirname(".."))
    from log import setup_logger
    from const import BCOLORS

    setup_logger()
    parser = Parser()
    with (open("parser/names.txt", "r", encoding="utf-8") as f):
        for name in f:
            if name != "":
                episode, tokens, name = parser.parse(name)
                if len(tokens) == 1:
                    logger.debug(f"{BCOLORS._(BCOLORS.HEADER, name)}")
                    logger.debug(f"{BCOLORS._(BCOLORS.OKGREEN,tokens)}")
                    logger.debug(f"{BCOLORS._(BCOLORS.WARNING,episode)}")
