"""NVIDIA NIM client with multi-key rotation. TO BUILD IN PHASE 7.

Requirements:
- OpenAI-compatible chat completions at settings.nim_base_url
- Rotate through settings.key_list; on 429 or 5xx move to the next key and retry
- Support `tools` (function calling) in requests
- No other LLM providers
"""
