"""
Answer comparison module supporting Exact, Contains, and Semantic comparison modes.
Semantic mode supports optional LLM evaluation (Gemini / OpenAI) with automatic
fallback to RapidFuzz token matching when no API keys are provided.
"""

import os
import re
import string
import json
from dataclasses import dataclass
from typing import Optional, Tuple
from dotenv import load_dotenv

# Load optional environment variables from .env
load_dotenv()

try:
    from rapidfuzz import fuzz
except ImportError:
    fuzz = None


@dataclass
class ComparisonResult:
    """Represents the outcome of comparing the actual answer against expected."""
    status: str      # 'PASS' or 'FAIL'
    score: float     # 0.0 to 100.0
    reason: str      # One-line explanation of the verdict
    mode_used: str   # 'exact', 'contains', 'semantic-llm', or 'semantic-fuzzy'


class AnswerComparator:
    def __init__(
        self,
        default_mode: str = "semantic",
        rapidfuzz_threshold: float = 80.0,
        llm_provider: str = "auto",
        gemini_model: str = "gemini-1.5-flash",
        openai_model: str = "gpt-4o-mini",
    ):
        self.default_mode = (default_mode or "semantic").lower()
        self.rapidfuzz_threshold = float(rapidfuzz_threshold)
        self.llm_provider = (llm_provider or "auto").lower()
        self.gemini_model = gemini_model
        self.openai_model = openai_model
        
        # Check available API keys
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()

    @staticmethod
    def normalize_text(text: Optional[str]) -> str:
        """
        Normalize text by converting to lowercase, stripping punctuation,
        and collapsing whitespace.
        """
        if not text:
            return ""
        # Lowercase
        s = str(text).lower()
        # Remove punctuation
        s = s.translate(str.maketrans("", "", string.punctuation))
        # Collapse multiple whitespace characters into a single space
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def compare(
        self,
        expected: str,
        actual: str,
        mode: Optional[str] = None
    ) -> ComparisonResult:
        """
        Compare actual answer with expected answer using specified or default mode.
        """
        mode = (mode or self.default_mode).lower().strip()
        
        if mode == "exact":
            return self._compare_exact(expected, actual)
        elif mode == "contains":
            return self._compare_contains(expected, actual)
        elif mode == "semantic":
            return self._compare_semantic(expected, actual)
        else:
            # Fallback to contains if mode is unrecognized
            return self._compare_contains(expected, actual)

    def _compare_exact(self, expected: str, actual: str) -> ComparisonResult:
        """Normalized exact match comparison."""
        norm_exp = self.normalize_text(expected)
        norm_act = self.normalize_text(actual)
        
        if norm_exp == norm_act:
            return ComparisonResult(
                status="PASS",
                score=100.0,
                reason="Normalized exact match",
                mode_used="exact"
            )
        else:
            # Calculate token similarity for informative score even on exact mismatch
            score = round(fuzz.ratio(norm_exp, norm_act), 1) if fuzz else 0.0
            return ComparisonResult(
                status="FAIL",
                score=score,
                reason="Normalized text differs from expected",
                mode_used="exact"
            )

    def _compare_contains(self, expected: str, actual: str) -> ComparisonResult:
        """Keyword and substring containment comparison."""
        norm_exp = self.normalize_text(expected)
        norm_act = self.normalize_text(actual)
        
        if not norm_exp:
            return ComparisonResult(
                status="PASS",
                score=100.0,
                reason="Expected answer is empty",
                mode_used="contains"
            )
            
        # 1. Direct normalized substring check
        if norm_exp in norm_act:
            return ComparisonResult(
                status="PASS",
                score=100.0,
                reason="Expected text appears directly in actual reply",
                mode_used="contains"
            )
            
        # 2. Check if all key expected words appear in actual reply
        exp_words = [w for w in norm_exp.split() if len(w) > 2]
        if exp_words:
            matched_words = [w for w in exp_words if w in norm_act]
            ratio = len(matched_words) / len(exp_words)
            score = round(ratio * 100.0, 1)
            
            if ratio == 1.0:
                return ComparisonResult(
                    status="PASS",
                    score=100.0,
                    reason="All expected keywords found in actual reply",
                    mode_used="contains"
                )
            elif ratio >= 0.8:
                return ComparisonResult(
                    status="PASS",
                    score=score,
                    reason=f"{len(matched_words)}/{len(exp_words)} keywords found ({score}%)",
                    mode_used="contains"
                )
            else:
                missing = [w for w in exp_words if w not in norm_act]
                return ComparisonResult(
                    status="FAIL",
                    score=score,
                    reason=f"Missing keywords: {', '.join(missing[:3])}",
                    mode_used="contains"
                )
                
        # Fallback if no words > 2 chars
        return ComparisonResult(
            status="FAIL",
            score=0.0,
            reason="Expected text not found in actual reply",
            mode_used="contains"
        )

    def _compare_semantic(self, expected: str, actual: str) -> ComparisonResult:
        """
        Semantic comparison: checks for LLM API keys first;
        if neither is set or if LLM call fails, falls back cleanly to RapidFuzz.
        """
        # Try LLM if configured and key is available
        if self.llm_provider in ["gemini", "auto"] and self.gemini_api_key:
            res = self._call_gemini_judge(expected, actual)
            if res:
                return res

        if self.llm_provider in ["openai", "auto"] and self.openai_api_key:
            res = self._call_openai_judge(expected, actual)
            if res:
                return res

        # Automatic fallback to RapidFuzz
        return self._compare_fuzzy_rapidfuzz(expected, actual)

    def _compare_fuzzy_rapidfuzz(self, expected: str, actual: str) -> ComparisonResult:
        """
        Fuzzy matching using RapidFuzz token_set_ratio.
        token_set_ratio handles reworded sentences, subsets, and extraneous chatter well.
        """
        if not fuzz:
            # If rapidfuzz is somehow not installed, fall back to contains
            return self._compare_contains(expected, actual)

        norm_exp = self.normalize_text(expected)
        norm_act = self.normalize_text(actual)

        if not norm_exp:
            return ComparisonResult(
                status="PASS",
                score=100.0,
                reason="Expected text is empty",
                mode_used="semantic-fuzzy"
            )

        # Direct containment shortcut
        if norm_exp in norm_act:
            return ComparisonResult(
                status="PASS",
                score=100.0,
                reason="Full expected phrase matched in actual reply",
                mode_used="semantic-fuzzy"
            )

        # Calculate token_set_ratio (handles extra words, order)
        token_set_score = fuzz.token_set_ratio(norm_exp, norm_act)
        partial_score = fuzz.partial_ratio(norm_exp, norm_act)
        
        # Best composite fuzzy score
        final_score = round(max(token_set_score, partial_score), 1)
        passed = final_score >= self.rapidfuzz_threshold

        status = "PASS" if passed else "FAIL"
        reason = (
            f"Fuzzy score {final_score}% >= threshold {self.rapidfuzz_threshold}%"
            if passed else
            f"Fuzzy score {final_score}% < threshold {self.rapidfuzz_threshold}%"
        )

        return ComparisonResult(
            status=status,
            score=final_score,
            reason=reason,
            mode_used="semantic-fuzzy"
        )

    def _call_gemini_judge(self, expected: str, actual: str) -> Optional[ComparisonResult]:
        """Judge semantic equivalence using Gemini API via HTTP request."""
        try:
            import requests
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_api_key}"
            prompt = (
                "You are an automated QA test judge comparing chatbot responses.\n"
                f"Expected Answer: \"{expected}\"\n"
                f"Actual Answer: \"{actual}\"\n\n"
                "Does the Actual Answer semantically convey the same meaning or answer the intent of Expected Answer?\n"
                "Respond ONLY with a JSON object in this exact schema:\n"
                "{\"verdict\": \"PASS\" | \"FAIL\", \"score\": <integer 0-100>, \"reason\": \"<one short sentence>\"}"
            )
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.0, "responseMimeType": "application/json"}
            }
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                parsed = json.loads(raw_text)
                return ComparisonResult(
                    status=parsed.get("verdict", "FAIL").upper(),
                    score=float(parsed.get("score", 0)),
                    reason=parsed.get("reason", "Evaluated by Gemini"),
                    mode_used="semantic-gemini"
                )
        except Exception:
            pass
        return None

    def _call_openai_judge(self, expected: str, actual: str) -> Optional[ComparisonResult]:
        """Judge semantic equivalence using OpenAI API via HTTP request."""
        try:
            import requests
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            prompt = (
                "You are an automated QA test judge comparing chatbot responses.\n"
                f"Expected Answer: \"{expected}\"\n"
                f"Actual Answer: \"{actual}\"\n\n"
                "Does the Actual Answer semantically convey the same meaning or fulfill the intent of Expected Answer?\n"
                "Respond ONLY with a JSON object in this exact schema:\n"
                "{\"verdict\": \"PASS\" | \"FAIL\", \"score\": <integer 0-100>, \"reason\": \"<one short sentence>\"}"
            )
            payload = {
                "model": self.openai_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                "response_format": {"type": "json_object"}
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                raw_text = data["choices"][0]["message"]["content"].strip()
                parsed = json.loads(raw_text)
                return ComparisonResult(
                    status=parsed.get("verdict", "FAIL").upper(),
                    score=float(parsed.get("score", 0)),
                    reason=parsed.get("reason", "Evaluated by OpenAI"),
                    mode_used="semantic-openai"
                )
        except Exception:
            pass
        return None
