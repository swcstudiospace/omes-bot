"""Phase 21: XClient behind a tweepy transport, stubbed at the client seam."""

from __future__ import annotations

import pytest
import tweepy

from omes.tools.x import MAX_MEDIA_BYTES, XClient, XError
from omes.tools.x_tweepy import TweepyTransport


class StubClient:
    """Records v2 calls and replays queued tweepy.Response objects."""

    def __init__(self, token: str, script: list):
        self.token = token
        self.script = script
        self.calls: list[tuple] = []

    def get_me(self, **kwargs):
        self.calls.append(("get_me", kwargs))
        return self.script.pop(0)

    def get_users_mentions(self, user_id, **kwargs):
        self.calls.append(("get_users_mentions", user_id, kwargs))
        return self.script.pop(0)

    def get_tweet(self, post_id, **kwargs):
        self.calls.append(("get_tweet", post_id, kwargs))
        return self.script.pop(0)

    def create_tweet(self, **kwargs):
        self.calls.append(("create_tweet", kwargs))
        return self.script.pop(0)


def _response(data=None, meta=None):
    return tweepy.Response(data=data, meta=meta or {}, errors=[], includes={})


def _made_client(script: list, fallback=None) -> tuple[XClient, list]:
    made: list[StubClient] = []
    shared = list(script)

    def make(token: str) -> StubClient:
        stub = StubClient(token, shared)
        made.append(stub)
        return stub

    transport = TweepyTransport(make_client=make, fallback=fallback)
    return XClient(transport, token="x-secret"), made


def test_me_and_reads_map_to_v2_calls():
    client, made = _made_client(
        [
            _response({"id": "bot-9", "name": "Omes", "username": "omesbot"}),
            _response({"id": "bot-9", "name": "Omes", "username": "omesbot"}),
            _response(
                [{"id": "m1", "text": "hi"}, {"id": "m2", "text": "yo"}],
                {"result_count": 2, "next_token": "tok-1"},
            ),
            _response({"id": "m1", "text": "hi"}),
        ]
    )
    assert client.me()["username"] == "omesbot"
    mentions = client.mentions(max_results=25)
    assert [post["id"] for post in mentions["posts"]] == ["m1", "m2"]
    assert mentions["next_token"] == "tok-1"
    assert client.read_post("m1") == {"id": "m1", "text": "hi"}

    assert made and made[0].token == "x-secret"
    calls = [call for stub in made for call in stub.calls]
    assert calls[0] == ("get_me", {"user_auth": False})
    assert calls[1] == ("get_me", {"user_auth": False})
    assert calls[2] == (
        "get_users_mentions",
        "bot-9",
        {"max_results": 25, "user_auth": False},
    )
    assert calls[3] == ("get_tweet", "m1", {"user_auth": False})


def test_mentions_passes_pagination_token():
    client, made = _made_client([_response([{"id": "m3"}], {"result_count": 1})])
    result = client.mentions(user_id="u-1", pagination_token="page-2")
    assert [post["id"] for post in result["posts"]] == ["m3"]
    assert made[0].calls == [
        (
            "get_users_mentions",
            "u-1",
            {"max_results": 10, "pagination_token": "page-2", "user_auth": False},
        )
    ]


def test_post_and_thread_map_reply_and_media():
    client, made = _made_client(
        [
            _response({"id": "p1", "text": "hello"}),
            _response({"id": "t1", "text": "one"}),
            _response({"id": "t2", "text": "two"}),
        ]
    )
    assert client.post("hello", reply_to="m1", media_ids=["mid-7"])["id"] == "p1"
    published = client.thread(["one", "two"])
    assert [post["id"] for post in published] == ["t1", "t2"]

    calls = [call for stub in made for call in stub.calls]
    assert calls[0] == (
        "create_tweet",
        {
            "text": "hello",
            "in_reply_to_tweet_id": "m1",
            "media_ids": ["mid-7"],
            "user_auth": False,
        },
    )
    assert calls[1][1]["text"] == "one"
    assert "in_reply_to_tweet_id" not in calls[1][1]
    assert calls[2][1] == {
        "text": "two",
        "in_reply_to_tweet_id": "t1",
        "user_auth": False,
    }


class _Fallback:
    def __init__(self):
        self.calls: list[tuple] = []

    def get(self, url, headers, params):
        self.calls.append(("GET", url, headers, params))
        return {}

    def post(self, url, headers, body):
        self.calls.append(("POST", url, headers, body))
        return {"media_id_string": "mid-9"}


def test_media_upload_routes_to_fallback():
    fallback = _Fallback()
    client, _ = _made_client([], fallback=fallback)
    assert client.upload_media(b"img-bytes") == {"media_id": "mid-9"}
    method, url, headers, body = fallback.calls[0]
    assert method == "POST"
    assert url == "https://upload.twitter.com/1.1/media/upload.json"
    assert headers == {"Authorization": "Bearer x-secret"}
    assert body["media_category"] == "tweet_image"
    assert len(fallback.calls) == 1


def test_media_upload_without_fallback_is_refused():
    client, _ = _made_client([])
    with pytest.raises(XError, match="media upload needs a raw HTTP fallback"):
        client.upload_media(b"img-bytes")


def test_tweepy_errors_become_x_errors_naming_the_endpoint():
    def explode(token: str):
        raise tweepy.TweepyException("boom")

    transport = TweepyTransport(make_client=explode)
    client = XClient(transport, token="x-secret")
    with pytest.raises(XError, match="2/users/me"):
        client.me()


def test_unknown_paths_need_a_fallback():
    transport = TweepyTransport(make_client=lambda token: StubClient(token, []))
    with pytest.raises(XError, match="unsupported"):
        transport.get(
            "https://api.x.com/2/users/search",
            {"Authorization": "Bearer [REDACTED]"},
            {},
        )


def test_blank_token_is_refused_before_any_client_call():
    made: list[str] = []
    transport = TweepyTransport(make_client=made.append)
    client = XClient(transport, token="  ")
    with pytest.raises(XError, match="no X credential"):
        client.me()
    assert made == []


def test_default_factory_builds_a_real_tweepy_client():
    transport = TweepyTransport()
    client = transport.make_client("x-secret")
    assert isinstance(client, tweepy.Client)
    assert client.bearer_token == "x-secret"
    assert MAX_MEDIA_BYTES == 5 * 1024 * 1024
