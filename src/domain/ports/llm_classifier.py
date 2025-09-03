from __future__ import annotations

from abc import ABC, abstractmethod


class LLMClassifier(ABC):
    """Port interface for LLM-powered tasks: classification and information extraction."""

    @abstractmethod
    def classify_document(self, easy_text: str, tess_text: str) -> str:
        pass

    @abstractmethod
    def extract_number_date(self, doc_type: str, easy_text: str, tess_text: str) -> str:
        pass

    @abstractmethod
    def extract_counterparties(self, doc_type: str, easy_text: str, tess_text: str) -> str:
        pass

    @abstractmethod
    def extract_requisites(self, parties_block: str, full_easy: str, full_tess: str) -> str:
        pass


