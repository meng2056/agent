from typing import Any
from PyQt5.QtCore import pyqtSignal
from langchain_core.callbacks import BaseCallbackHandler


class GUICallbackHandler(BaseCallbackHandler):
    def __init__(
            self,
            new_text_sig: pyqtSignal(str)
    ):
        self.new_text_sig = new_text_sig

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        self.new_text_sig.emit(token)