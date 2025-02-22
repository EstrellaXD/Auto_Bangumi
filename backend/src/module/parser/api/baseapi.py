from abc import ABC, abstractmethod


class BaseAPI(ABC):
    @abstractmethod
    async def fetch_content(self,key_word:str)->dict[str,str]:
        pass


