"""
Answer comparison module (Judge) supporting Exact, Contains, and Semantic modes.
Semantic mode defaults to RapidFuzz token matching (threshold 80) and supports
optional pluggable LLM evaluation (Gemini / OpenAI) via environment variables.
"""

import os
import re
import string
import json
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

try:
    from rapidfuzz import fuzz
except ImportError:
    fuzz = None


@dataclass
class ComparisonResult:
    """Outcome of comparing actual answer against expected answer."""
    status: str       # 'PASS' or 'FAIL'
    score: float      # 0.0 to 100.0
    reason: str       # Clear one-line explanation
    mode_used: str    # 'exact', 'contains', 'semantic-llm', or 'semantic-fuzzy'


class AnswerJudge:
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
        
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()

    @staticmethod
    def normalize_text(text: Optional[str]) -> str:
        """Lowercase, remove punctuation, collapse whitespace."""
        if not text:
            return ""
        s = str(text).lower()
        s = s.translate(str.maketrans("", "", string.punctuation))
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def compare(
        self,
        expected: str,
        actual: str,
        mode: Optional[str] = None
    ) -> ComparisonResult:
        """Compare actual with expected under chosen mode."""
        mode = (mode or self.default_mode).lower().strip()
        
        if mode == "exact":
            return self._compare_exact(expected, actual)
        elif mode == "contains":
            return self._compare_contains(expected, actual)
        elif mode == "semantic":
            return self._compare_semantic(expected, actual)
        else:
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
            
        if norm_exp in norm_act:
            return ComparisonResult(
                status="PASS",
                score=100.0,
                reason="Expected text appears directly in actual reply",
                mode_used="contains"
            )
            
        exp_words = [w for w in norm_exp.split() if len(w) > 2]
        if exp_words:
            matched = [w for w in exp_words if w in norm_act]
            ratio = len(matched) / len(exp_words)
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
                    reason=f"{len(matched)}/{len(exp_words)} keywords found ({score}%)",
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
                
        return ComparisonResult(
            status="FAIL",
            score=0.0,
            reason="Expected text not found in actual reply",
            mode_used="contains"
        )

    def _compare_semantic(self, expected: str, actual: str) -> ComparisonResult:
        """
        Semantic match: checks for LLM API keys first;
        if neither is set or if LLM call fails, falls back cleanly to RapidFuzz.
        """
        if self.llm_provider in ["gemini", "auto"] and self.gemini_api_key:
            res = self._call_gemini_judge(expected, actual)
            if res:
                return res

        if self.llm_provider in ["openai", "auto"] and self.openai_api_key:
            res = self._call_openai_judge(expected, actual)
            if res:
                return res

        return self._compare_fuzzy_rapidfuzz(expected, actual)

    def _compare_fuzzy_rapidfuzz(self, expected: str, actual: str) -> ComparisonResult:
        """Fuzzy matching using composite RapidFuzz token_set_ratio & partial_ratio."""
        if not fuzz:
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

        if norm_exp in norm_act:
            return ComparisonResult(
                status="PASS",
                score=100.0,
                reason="Full expected phrase matched in actual reply",
                mode_used="semantic-fuzzy"
            )

        token_set_score = fuzz.token_set_ratio(norm_exp, norm_act)
        partial_score = fuzz.partial_ratio(norm_exp, norm_act)
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
        """Judge semantic equivalence using Gemini API."""
        try:
            import requests
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_api_key}"
            prompt = (
                "You are an automated QA test judge comparing chatbot responses.\n"
                f"Expected Answer: \"{expected}\"\n"
                f"Actual Answer: \"{actual}\"\n\n"
                "Does the Actual Answer semantically convey the same meaning or fulfill the intent of Expected Answer?\n"
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

    def verify_input_acceptance(self, bot_reply: str, submitted_input: str) -> tuple:
        """
        Verifies whether the bot accepted or rejected the submitted user input.
        Returns: (is_accepted: bool, detail_message: str)
        """
        if not bot_reply:
            return (True, "Bot accepted input")

        b_low = bot_reply.lower()

        # Common validation rejection keywords across chatbots
        rejection_patterns = [
            "please enter valid",
            "enter a valid",
            "not a valid",
            "is not valid",
            "invalid phone",
            "invalid mobile",
            "invalid email",
            "invalid number",
            "invalid name",
            "invalid input",
            "invalid date",
            "try again",
            "try entering",
            "incorrect format",
            "format is incorrect",
            "must be at least",
            "doesn't look like a valid",
            "does not look like a valid",
            "could not understand",
            "please provide a valid",
            "please provide valid",
            "10 digit",
            "10-digit"
        ]

        # 1. Try Gemini LLM if configured
        if self.gemini_api_key:
            try:
                import requests
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_api_key}"
                prompt = (
                    "You are an automated QA test judge verifying chatbot input validation.\n"
                    f"User submitted input: \"{submitted_input}\"\n"
                    f"Chatbot subsequent reply: \"{bot_reply}\"\n\n"
                    "Did the chatbot reject or fail the user's input with a validation error (e.g. invalid phone, invalid email, try again)?\n"
                    "Respond with a JSON object: {\"accepted\": true | false, \"reason\": \"<short one-line summary>\"}"
                )
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.0, "responseMimeType": "application/json"}
                }
                resp = requests.post(url, json=payload, timeout=6)
                if resp.status_code == 200:
                    data = resp.json()
                    parsed = json.loads(data["candidates"][0]["content"]["parts"][0]["text"])
                    accepted = bool(parsed.get("accepted", True))
                    reason = str(parsed.get("reason", "Verified by Gemini"))
                    return (accepted, reason)
            except Exception:
                pass

        # 2. Try OpenAI LLM if configured
        if self.openai_api_key:
            try:
                import requests
                url = "https://api.openai.com/v1/chat/completions"
                headers = {"Authorization": f"Bearer {self.openai_api_key}", "Content-Type": "application/json"}
                prompt = (
                    "You are an automated QA test judge verifying chatbot input validation.\n"
                    f"User submitted input: \"{submitted_input}\"\n"
                    f"Chatbot subsequent reply: \"{bot_reply}\"\n\n"
                    "Did the chatbot reject or fail the user's input with a validation error (e.g. invalid phone, invalid email, try again)?\n"
                    "Respond with a JSON object: {\"accepted\": true | false, \"reason\": \"<short one-line summary>\"}"
                )
                payload = {
                    "model": self.openai_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.0,
                    "response_format": {"type": "json_object"}
                }
                resp = requests.post(url, headers=headers, json=payload, timeout=6)
                if resp.status_code == 200:
                    data = resp.json()
                    parsed = json.loads(data["choices"][0]["message"]["content"])
                    accepted = bool(parsed.get("accepted", True))
                    reason = str(parsed.get("reason", "Verified by OpenAI"))
                    return (accepted, reason)
            except Exception:
                pass

        # 3. Deterministic pattern matching
        for pattern in rejection_patterns:
            if pattern in b_low:
                # Extract first matching line or sentence
                lines = [l.strip() for l in bot_reply.split("\n") if pattern in l.lower()]
                matched_line = lines[0] if lines else pattern
                return (False, f"Validation Error: {matched_line}")

        return (True, "Bot accepted input and proceeded to next step")

    def match_prompt_to_candidate_queries(
        self,
        bot_prompt: str,
        candidate_queries: list
    ) -> tuple:
        """
        Intelligently matches a live bot prompt to one of the candidate queries in the test suite.
        Uses Gemini / OpenAI LLM if an API key is available; otherwise uses high-accuracy semantic intent & token matching.
        Works regardless of row order (whether the question is first, last, or anywhere in between).
        Returns: (best_index, confidence_score)
        """
        if not candidate_queries:
            return (0, 0.0)

        # 1. Try Gemini LLM if configured
        if self.gemini_api_key:
            try:
                import requests
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_api_key}"
                formatted = "\n".join([f"{i}. \"{q}\"" for i, q in enumerate(candidate_queries)])
                sys_prompt = (
                    "You are an automated QA test matcher for a conversational chatbot.\n"
                    f"The bot just asked this in the chat:\n\"{bot_prompt}\"\n\n"
                    f"Which of these candidate test queries does this prompt correspond to?\n{formatted}\n\n"
                    "Respond with a JSON object: {\"index\": <integer 0-based>, \"confidence\": <float 0-100>}"
                )
                payload = {
                    "contents": [{"parts": [{"text": sys_prompt}]}],
                    "generationConfig": {"temperature": 0.0, "responseMimeType": "application/json"}
                }
                resp = requests.post(url, json=payload, timeout=8)
                if resp.status_code == 200:
                    data = resp.json()
                    parsed = json.loads(data["candidates"][0]["content"]["parts"][0]["text"])
                    idx = int(parsed.get("index", 0))
                    conf = float(parsed.get("confidence", 95.0))
                    if 0 <= idx < len(candidate_queries):
                        return (idx, conf)
            except Exception:
                pass

        # 2. Try OpenAI LLM if configured
        if self.openai_api_key:
            try:
                import requests
                url = "https://api.openai.com/v1/chat/completions"
                headers = {"Authorization": f"Bearer {self.openai_api_key}", "Content-Type": "application/json"}
                formatted = "\n".join([f"{i}. \"{q}\"" for i, q in enumerate(candidate_queries)])
                sys_prompt = (
                    "You are an automated QA test matcher for a conversational chatbot.\n"
                    f"The bot just asked this in the chat:\n\"{bot_prompt}\"\n\n"
                    f"Which of these candidate test queries does this prompt correspond to?\n{formatted}\n\n"
                    "Respond with a JSON object: {\"index\": <integer 0-based>, \"confidence\": <float 0-100>}"
                )
                payload = {
                    "model": self.openai_model,
                    "messages": [{"role": "user", "content": sys_prompt}],
                    "temperature": 0.0,
                    "response_format": {"type": "json_object"}
                }
                resp = requests.post(url, headers=headers, json=payload, timeout=8)
                if resp.status_code == 200:
                    data = resp.json()
                    parsed = json.loads(data["choices"][0]["message"]["content"])
                    idx = int(parsed.get("index", 0))
                    conf = float(parsed.get("confidence", 95.0))
                    if 0 <= idx < len(candidate_queries):
                        return (idx, conf)
            except Exception:
                pass

        # 3. Fallback: Semantic Intent + RapidFuzz Composite Matcher
        b_low = bot_prompt.lower().strip()
        intent_map = {
            'name': ['name', 'who are you', 'know your name', 'full name', 'call you'],
            'phone': ['phone', 'mobile', 'contact', 'number', 'cell', 'digits'],
            'email': ['email', 'mail', 'e-mail'],
            'address': ['address', 'permanent', 'city', 'location', 'residence', 'street'],
            'date': ['date', 'calendar', 'schedule', 'day', 'month', 'time', 'appointment', 'select a date'],
            'rating': ['rate', 'rating', 'feedback', 'experience', 'review', 'emoji', 'star'],
            'submit': ['submit', 'finish', 'end']
        }

        scores = []
        for idx, q in enumerate(candidate_queries):
            q_low = str(q).lower().strip()
            score = 0.0

            if q_low in b_low or b_low in q_low:
                score = 100.0
            else:
                for cat, kws in intent_map.items():
                    in_b = any(k in b_low for k in kws)
                    in_q = any(k in q_low for k in kws)
                    if in_b and in_q:
                        score = max(score, 95.0)

                if fuzz:
                    fuzz_score = max(
                        float(fuzz.token_set_ratio(b_low, q_low)),
                        float(fuzz.partial_ratio(b_low, q_low))
                    )
                    score = max(score, fuzz_score)
            scores.append((idx, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[0] if scores else (0, 0.0)

    def _call_openai_judge(self, expected: str, actual: str) -> Optional[ComparisonResult]:
        """Judge semantic equivalence using OpenAI API."""
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

    def verify_input_acceptance(self, bot_reply: str, submitted_input: str) -> tuple:
        """
        Verifies whether the bot accepted or rejected the submitted user input.
        Returns: (is_accepted: bool, detail_message: str)
        """
        if not bot_reply:
            return (True, "Bot accepted input")

        b_low = bot_reply.lower()

        # Common validation rejection keywords across chatbots
        rejection_patterns = [
            "please enter valid",
            "enter a valid",
            "not a valid",
            "is not valid",
            "invalid phone",
            "invalid mobile",
            "invalid email",
            "invalid number",
            "invalid name",
            "invalid input",
            "invalid date",
            "try again",
            "try entering",
            "incorrect format",
            "format is incorrect",
            "must be at least",
            "doesn't look like a valid",
            "does not look like a valid",
            "could not understand",
            "please provide a valid",
            "please provide valid",
            "10 digit",
            "10-digit"
        ]

        # 1. Try Gemini LLM if configured
        if self.gemini_api_key:
            try:
                import requests
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_api_key}"
                prompt = (
                    "You are an automated QA test judge verifying chatbot input validation.\n"
                    f"User submitted input: \"{submitted_input}\"\n"
                    f"Chatbot subsequent reply: \"{bot_reply}\"\n\n"
                    "Did the chatbot reject or fail the user's input with a validation error (e.g. invalid phone, invalid email, try again)?\n"
                    "Respond with a JSON object: {\"accepted\": true | false, \"reason\": \"<short one-line summary>\"}"
                )
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.0, "responseMimeType": "application/json"}
                }
                resp = requests.post(url, json=payload, timeout=6)
                if resp.status_code == 200:
                    data = resp.json()
                    parsed = json.loads(data["candidates"][0]["content"]["parts"][0]["text"])
                    accepted = bool(parsed.get("accepted", True))
                    reason = str(parsed.get("reason", "Verified by Gemini"))
                    return (accepted, reason)
            except Exception:
                pass

        # 2. Try OpenAI LLM if configured
        if self.openai_api_key:
            try:
                import requests
                url = "https://api.openai.com/v1/chat/completions"
                headers = {"Authorization": f"Bearer {self.openai_api_key}", "Content-Type": "application/json"}
                prompt = (
                    "You are an automated QA test judge verifying chatbot input validation.\n"
                    f"User submitted input: \"{submitted_input}\"\n"
                    f"Chatbot subsequent reply: \"{bot_reply}\"\n\n"
                    "Did the chatbot reject or fail the user's input with a validation error (e.g. invalid phone, invalid email, try again)?\n"
                    "Respond with a JSON object: {\"accepted\": true | false, \"reason\": \"<short one-line summary>\"}"
                )
                payload = {
                    "model": self.openai_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.0,
                    "response_format": {"type": "json_object"}
                }
                resp = requests.post(url, headers=headers, json=payload, timeout=6)
                if resp.status_code == 200:
                    data = resp.json()
                    parsed = json.loads(data["choices"][0]["message"]["content"])
                    accepted = bool(parsed.get("accepted", True))
                    reason = str(parsed.get("reason", "Verified by OpenAI"))
                    return (accepted, reason)
            except Exception:
                pass

        # 3. Deterministic pattern matching
        for pattern in rejection_patterns:
            if pattern in b_low:
                # Extract first matching line or sentence
                lines = [l.strip() for l in bot_reply.split("\n") if pattern in l.lower()]
                matched_line = lines[0] if lines else pattern
                return (False, f"Validation Error: {matched_line}")

        return (True, "Bot accepted input and proceeded to next step")

    def match_prompt_to_candidate_queries(
        self,
        bot_prompt: str,
        candidate_queries: list
    ) -> tuple:
        """
        Intelligently matches a live bot prompt to one of the candidate queries in the test suite.
        Uses Gemini / OpenAI LLM if an API key is available; otherwise uses high-accuracy semantic intent & token matching.
        Works regardless of row order (whether the question is first, last, or anywhere in between).
        Returns: (best_index, confidence_score)
        """
        if not candidate_queries:
            return (0, 0.0)

        # 1. Try Gemini LLM if configured
        if self.gemini_api_key:
            try:
                import requests
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_api_key}"
                formatted = "\n".join([f"{i}. \"{q}\"" for i, q in enumerate(candidate_queries)])
                sys_prompt = (
                    "You are an automated QA test matcher for a conversational chatbot.\n"
                    f"The bot just asked this in the chat:\n\"{bot_prompt}\"\n\n"
                    f"Which of these candidate test queries does this prompt correspond to?\n{formatted}\n\n"
                    "Respond with a JSON object: {\"index\": <integer 0-based>, \"confidence\": <float 0-100>}"
                )
                payload = {
                    "contents": [{"parts": [{"text": sys_prompt}]}],
                    "generationConfig": {"temperature": 0.0, "responseMimeType": "application/json"}
                }
                resp = requests.post(url, json=payload, timeout=8)
                if resp.status_code == 200:
                    data = resp.json()
                    parsed = json.loads(data["candidates"][0]["content"]["parts"][0]["text"])
                    idx = int(parsed.get("index", 0))
                    conf = float(parsed.get("confidence", 95.0))
                    if 0 <= idx < len(candidate_queries):
                        return (idx, conf)
            except Exception:
                pass

        # 2. Try OpenAI LLM if configured
        if self.openai_api_key:
            try:
                import requests
                url = "https://api.openai.com/v1/chat/completions"
                headers = {"Authorization": f"Bearer {self.openai_api_key}", "Content-Type": "application/json"}
                formatted = "\n".join([f"{i}. \"{q}\"" for i, q in enumerate(candidate_queries)])
                sys_prompt = (
                    "You are an automated QA test matcher for a conversational chatbot.\n"
                    f"The bot just asked this in the chat:\n\"{bot_prompt}\"\n\n"
                    f"Which of these candidate test queries does this prompt correspond to?\n{formatted}\n\n"
                    "Respond with a JSON object: {\"index\": <integer 0-based>, \"confidence\": <float 0-100>}"
                )
                payload = {
                    "model": self.openai_model,
                    "messages": [{"role": "user", "content": sys_prompt}],
                    "temperature": 0.0,
                    "response_format": {"type": "json_object"}
                }
                resp = requests.post(url, headers=headers, json=payload, timeout=8)
                if resp.status_code == 200:
                    data = resp.json()
                    parsed = json.loads(data["choices"][0]["message"]["content"])
                    idx = int(parsed.get("index", 0))
                    conf = float(parsed.get("confidence", 95.0))
                    if 0 <= idx < len(candidate_queries):
                        return (idx, conf)
            except Exception:
                pass

        # 3. Fallback: Semantic Intent + RapidFuzz Composite Matcher
        b_low = bot_prompt.lower().strip()
        intent_map = {
            'name': ['name', 'who are you', 'know your name', 'full name', 'call you'],
            'phone': ['phone', 'mobile', 'contact', 'number', 'cell', 'digits'],
            'email': ['email', 'mail', 'e-mail'],
            'address': ['address', 'permanent', 'city', 'location', 'residence', 'street'],
            'date': ['date', 'calendar', 'schedule', 'day', 'month', 'time', 'appointment', 'select a date'],
            'rating': ['rate', 'rating', 'feedback', 'experience', 'review', 'emoji', 'star'],
            'submit': ['submit', 'finish', 'end']
        }

        scores = []
        for idx, q in enumerate(candidate_queries):
            q_low = str(q).lower().strip()
            score = 0.0

            if q_low in b_low or b_low in q_low:
                score = 100.0
            else:
                for cat, kws in intent_map.items():
                    in_b = any(k in b_low for k in kws)
                    in_q = any(k in q_low for k in kws)
                    if in_b and in_q:
                        score = max(score, 95.0)

                if fuzz:
                    fuzz_score = max(
                        float(fuzz.token_set_ratio(b_low, q_low)),
                        float(fuzz.partial_ratio(b_low, q_low))
                    )
                    score = max(score, fuzz_score)
            scores.append((idx, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[0] if scores else (0, 0.0)
