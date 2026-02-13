import re
import copy
import os
import sys
import logging
import datetime
from pathlib import Path
from typing import Any
from langchain_core.embeddings import Embeddings
from py_lib.general_func import general_func
import requests


class SpecEmbeddings(Embeddings):
    def __init__(
            self,
            tokenizer,
            base_url: str,
            model_name: str,
            api_key: str | None = None,
            max_length: int = 512
    ):
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        self.tokenizer = tokenizer
        self.model_name = model_name
        self.api_key = api_key
        self.max_length = max_length
        self.embedding_url = base_url

    def _prepare_input(self, txt: str) -> dict[str, Any]:
        encoded = self.tokenizer(
            txt,
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors="pt",
        )

        payload = {
            "input": txt,
            "model": self.model_name,
            "encoded_input": {
                "input_ids": encoded["input_ids"].tolist(),
                "attention_mask": encoded["attention_mask"].tolist(),
            }
        }
        return payload

    def _get_embeddings(self, txt: str) -> list[float]:
        payload = self._prepare_input(txt)
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            response = requests.post(
                self.embedding_url,
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            embedding_response = response.json()
            if "data" in embedding_response and len(embedding_response["data"])> 0:
                ebd = embedding_response["data"][0].get("embedding")
            else:
                ebd = []
            return ebd
        except Exception as e:
            raise RuntimeError(f"Error occurred while calling the API: {e}")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._get_embeddings(txt) for txt in texts]

    def embed_query(self, txt: str) -> list[float]:
        return self._get_embeddings(txt)