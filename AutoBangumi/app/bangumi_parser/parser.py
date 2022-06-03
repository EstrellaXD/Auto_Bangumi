import logging

logger = logging.getLogger(__name__)

from preprocessor import Preprocessor
from token_generator import TokenGenerator
from analyser import Analyser
from Tag import *


class Parser:
    def __init__(self) -> None:
        self._preprocessor = Preprocessor()
        self._token_generator = TokenGenerator()
        self._analyser = Analyser()

    def parse(self, name: str):
        name = self._preprocessor.preprocess(name)
        tokens = self._token_generator.generate(name)
        episode = self._analyser.analyse(name, tokens)
        dpi = get_dpi(name)
        lang = get_language(name)
        code = get_code(name)
        _type = get_type(name)
        vision = get_vision(name)
        ass = get_ass(name)
        return episode, tokens, name, dpi, lang, code, _type, vision, ass


if __name__ == "__main__":
    import os, sys

    sys.path.append(os.path.dirname(".."))
    sys.path.append(os.path.dirname("../utils"))

    from log import setup_logger
    from const import BCOLORS

    setup_logger()
    parser = Parser()
    with open("names.txt", "r", encoding="utf-8") as f:
        for name in f:
            if name != "":
                episode, tokens, name, dpi, lang, code, _type, vision, ass = parser.parse(name)
                if len(tokens) == 1:
                    logger.debug(f"{BCOLORS._(BCOLORS.HEADER, name)}")
                    logger.debug(f"{BCOLORS._(BCOLORS.OKGREEN, tokens)}")
                    logger.debug(f"{BCOLORS._(BCOLORS.WARNING, episode)}")
                    logger.debug(f"{BCOLORS._(BCOLORS.WARNING, dpi)}")
                    logger.debug(f"{BCOLORS._(BCOLORS.WARNING, lang)}")
                    logger.debug(f"{BCOLORS._(BCOLORS.WARNING, code)}")
                    logger.debug(f"{BCOLORS._(BCOLORS.WARNING, _type)}")
                    logger.debug(f"{BCOLORS._(BCOLORS.WARNING, vision)}")
                    logger.debug(f"{BCOLORS._(BCOLORS.WARNING, ass)}")
