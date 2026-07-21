#!/usr/bin/env python3.8

import json
import abc
import shlex
import hashlib
import typing as t
from utils import dict_2_obj
from flask import request, jsonify
from decrypt import AESCipher


class Event(object):
    callback_handler = None

    # event base
    def __init__(self, dict_data, token, encrypt_key):
        # event check and init
        header = dict_data.get("header")
        event = dict_data.get("event")
        if header is None or event is None:
            raise InvalidEventException("request is not callback event(v2)")
        self.header = dict_2_obj(header)
        self.event = dict_2_obj(event)
        self._validate(token, encrypt_key)

    def _validate(self, token, encrypt_key):
        encrypt_key = encrypt_key or ""
        if self.header.token != token:
            raise InvalidEventException("invalid token")
        timestamp = request.headers.get("X-Lark-Request-Timestamp")
        nonce = request.headers.get("X-Lark-Request-Nonce")
        signature = request.headers.get("X-Lark-Signature")
        body = request.data

        bytes_b1 = (timestamp + nonce + encrypt_key).encode("utf-8")
        bytes_b = bytes_b1 + body
        h = hashlib.sha256(bytes_b)
        if signature != h.hexdigest():
            raise InvalidEventException("invalid signature in event")

    @abc.abstractmethod
    def event_type(self):
        return self.header.event_type


class MessageReceiveEvent(Event):
    # message receive event defined in https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/im-v1/message/events/receive

    @staticmethod
    def event_type():
        return "im.message.receive_v1"

class MessageReactionCreatedEvent(Event):
    # message receive event defined in https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/im-v1/message/events/receive

    @staticmethod
    def event_type():
        return "im.message.reaction.created_v1"


class UrlVerificationEvent(Event):

    # special event: url verification event
    def __init__(self, dict_data):
        self.event = dict_2_obj(dict_data)

    @staticmethod
    def event_type():
        return "url_verification"


class EventManager(object):
    event_callback_map = dict()
    event_type_map = dict()
    _event_list = [MessageReceiveEvent, UrlVerificationEvent, MessageReactionCreatedEvent]
    FORWARD_TARGET_URL = "http://magika.bytedance.net/magika/api/v1/channels/lark/events"

    def __init__(self):
        for event in EventManager._event_list:
            EventManager.event_type_map[event.event_type()] = event

    def register(self, event_type: str) -> t.Callable:
        def decorator(f: t.Callable) -> t.Callable:
            self.register_handler_with_event_type(event_type=event_type, handler=f)
            return f

        return decorator

    @staticmethod
    def register_handler_with_event_type(event_type, handler):
        EventManager.event_callback_map[event_type] = handler

    @staticmethod
    def get_handler_with_event(token, encrypt_key):
        dict_data = json.loads(request.data)
        print("get_handler_with_event", dict_data)
        dict_data = EventManager._decrypt_data(encrypt_key, dict_data)
        callback_type = dict_data.get("type")
        # only verification data has callback_type, else is event
        if callback_type == "url_verification":
            event = UrlVerificationEvent(dict_data)
            return EventManager.event_callback_map.get(event.event_type()), event

        EventManager.print_forward_curl_command()
        # only handle event v2
        schema = dict_data.get("schema")
        if schema is None:
            raise InvalidEventException("request is not callback event(v2)")

        # get event_type
        event_type = dict_data.get("header").get("event_type")
        print("get_handler_with_event event_type", event_type)
        print("get_handler_with_event event_type_map", EventManager.event_type_map)
        print("get_handler_with_event callback map", EventManager.event_callback_map)
        # build event

        event = EventManager.event_type_map.get(event_type)(dict_data, token, encrypt_key)
        # get handler
        return EventManager.event_callback_map.get(event_type), event

    @staticmethod
    def print_forward_curl_command():
        body_text = request.get_data(as_text=True)
        headers = [
            ("Accept-Encoding", request.headers.get("Accept-Encoding", "gzip")),
            (
                "Content-Type",
                request.headers.get("Content-Type", "application/json;charset=utf-8"),
            ),
            (
                "X-Lark-Request-Nonce",
                request.headers.get("X-Lark-Request-Nonce", ""),
            ),
            (
                "X-Lark-Request-Timestamp",
                request.headers.get("X-Lark-Request-Timestamp", ""),
            ),
            ("X-Lark-Signature", request.headers.get("X-Lark-Signature", "")),
            ("X-Request-Id", request.headers.get("X-Request-Id", "")),
            ("X-Tt-Env", request.headers.get("X-Tt-Env", "")),
        ]

        cmd_parts = [
            "curl -X POST {}".format(shlex.quote(EventManager.FORWARD_TARGET_URL)),
        ]
        for key, value in headers:
            cmd_parts.append("-H {}".format(shlex.quote("{}: {}".format(key, value))))
        cmd_parts.append("--data-raw {}".format(shlex.quote(body_text)))

        print("Forward curl command:\n{}".format(" \\\n  ".join(cmd_parts)))

    @staticmethod
    def _decrypt_data(encrypt_key, data):
        encrypt_key = encrypt_key or ""
        encrypt_data = data.get("encrypt")
        if encrypt_key == "" and encrypt_data is None:
            # data haven't been encrypted
            return data
        if encrypt_key == "":
            raise Exception("ENCRYPT_KEY is necessary")
        cipher = AESCipher(encrypt_key)

        return json.loads(cipher.decrypt_string(encrypt_data))


class InvalidEventException(Exception):
    def __init__(self, error_info):
        self.error_info = error_info

    def __str__(self) -> str:
        return "Invalid event: {}".format(self.error_info)

    __repr__ = __str__
