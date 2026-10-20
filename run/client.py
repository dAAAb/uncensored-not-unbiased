"""Minimal OpenAI-compatible chat client (standard library only), for llama.cpp llama-server, Strata or any
/v1/chat/completions endpoint. Thinking is switched off through chat_template_kwargs, which both servers honour."""
import json
import time
import urllib.error
import urllib.request


class Chat:
    def __init__(self, base_url, model="local", api_key=None, timeout=900):
        self.url = base_url.rstrip("/") + "/v1/chat/completions"
        self.model = model
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
        self.timeout = timeout

    def __call__(self, messages, max_tokens=512, temperature=0.0, top_p=1.0, logprobs=0, seed=None, retries=3):
        body = {"model": self.model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature,
                "top_p": top_p, "stream": False, "chat_template_kwargs": {"enable_thinking": False}}
        if logprobs:
            body["logprobs"] = True
            body["top_logprobs"] = logprobs
        if seed is not None:
            body["seed"] = seed
        data = json.dumps(body).encode("utf-8")
        for attempt in range(retries):
            try:
                t0 = time.time()
                req = urllib.request.Request(self.url, data=data, headers=self.headers)
                resp = json.load(urllib.request.urlopen(req, timeout=self.timeout))
                resp["_wall_s"] = round(time.time() - t0, 3)
                return resp
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                if attempt == retries - 1:
                    raise
                time.sleep(5 * (attempt + 1))
                last = e  # noqa: F841


def first_token_logprobs(resp):
    """Top alternatives for the first generated token as {token_text: probability}, or None if not provided."""
    try:
        content = resp["choices"][0]["logprobs"]["content"]
    except (KeyError, TypeError, IndexError):
        return None
    if not content:
        return None
    import math
    return {alt["token"]: math.exp(alt["logprob"]) for alt in content[0].get("top_logprobs", [])}


def answer_text(resp):
    msg = resp["choices"][0]["message"]
    return msg.get("content") or ""
