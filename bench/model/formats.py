"""The three API formats of the mock model's replies."""

from model.requests import CONTEXT_TOKENS
from workload import chunks

# Each API format as a stream of (event name, value, paced text). The server
# writes `value` as one server-sent event, and paces it by `paced text`.


def chat_stream(body, request_id, thinking, answer, call, input_tokens):
    def chunk(delta, finish=None, usage=None, paced=""):
        value = {
            "id": f"chatcmpl-{request_id}",
            "object": "chat.completion.chunk",
            "created": 0,
            "model": body.get("model", "mock-model"),
            "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
        }
        if usage:
            value["usage"] = usage
        return None, value, paced

    yield chunk({"role": "assistant"})
    for field, value in [("reasoning_content", thinking), ("content", answer)]:
        for text in chunks(value):
            yield chunk({field: text}, paced=text)
    if call:
        call_id, name, args = call
        yield chunk(
            {
                "tool_calls": [
                    {
                        "index": 0,
                        "id": call_id,
                        "type": "function",
                        "function": {"name": name, "arguments": ""},
                    }
                ]
            }
        )
        for text in chunks(args):
            delta = {"tool_calls": [{"index": 0, "function": {"arguments": text}}]}
            yield chunk(delta, paced=text)
    output_tokens = (
        len(thinking) + len(answer) + (len(call[2]) if call else 0) + 3
    ) // 4
    yield chunk(
        {},
        "tool_calls" if call else "stop",
        usage={
            "prompt_tokens": input_tokens,
            "completion_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        },
    )
    yield None, "[DONE]", ""


def anthropic_stream(body, request_id, thinking, answer, call, input_tokens):
    def event(kind, paced="", **fields):
        return kind, {"type": kind, **fields}, paced

    yield event(
        "message_start",
        message={
            "id": f"msg_{request_id}",
            "type": "message",
            "role": "assistant",
            "model": body.get("model"),
            "content": [],
            "stop_reason": None,
            "stop_sequence": None,
            "usage": {"input_tokens": input_tokens, "output_tokens": 0},
        },
    )
    index = 0
    for kind, value in [("thinking", thinking), ("text", answer)]:
        if not value:
            continue
        yield event(
            "content_block_start", index=index, content_block={"type": kind, kind: ""}
        )
        for text in chunks(value):
            yield event(
                "content_block_delta",
                text,
                index=index,
                delta={"type": kind + "_delta", kind: text},
            )
        if kind == "thinking":
            yield event(
                "content_block_delta",
                index=index,
                delta={"type": "signature_delta", "signature": "benchmark-signature"},
            )
        yield event("content_block_stop", index=index)
        index += 1
    if call:
        call_id, name, args = call
        yield event(
            "content_block_start",
            index=index,
            content_block={
                "type": "tool_use",
                "id": call_id,
                "name": name,
                "input": {},
            },
        )
        for text in chunks(args):
            yield event(
                "content_block_delta",
                text,
                index=index,
                delta={"type": "input_json_delta", "partial_json": text},
            )
        yield event("content_block_stop", index=index)
    streamed = len(thinking) + len(answer) + (len(call[2]) if call else 0)
    yield event(
        "message_delta",
        delta={
            "stop_reason": "tool_use" if call else "end_turn",
            "stop_sequence": None,
        },
        usage={"output_tokens": streamed // 4},
    )
    yield event("message_stop")


def responses_stream(body, request_id, thinking, answer, call, input_tokens):
    def event(kind, paced="", **fields):
        return kind, {"type": kind, **fields}, paced

    output = []
    yield event(
        "response.created",
        response={
            "id": f"resp_{request_id}",
            "object": "response",
            "status": "in_progress",
            "output": [],
        },
    )
    if thinking:
        item = {"id": "rs_bench", "type": "reasoning", "summary": []}
        part = {"item_id": item["id"], "output_index": 0, "summary_index": 0}
        yield event("response.output_item.added", output_index=0, item=item)
        yield event(
            "response.reasoning_summary_part.added",
            **part,
            part={"type": "summary_text", "text": ""},
        )
        for text in chunks(thinking):
            yield event(
                "response.reasoning_summary_text.delta", text, **part, delta=text
            )
        item["summary"] = [{"type": "summary_text", "text": thinking}]
        yield event("response.reasoning_summary_text.done", **part, text=thinking)
        yield event(
            "response.reasoning_summary_part.done", **part, part=item["summary"][0]
        )
        yield event("response.output_item.done", output_index=0, item=item)
        output.append(item)
    index = len(output)
    item = {
        "id": f"msg_{request_id}",
        "type": "message",
        "role": "assistant",
        "status": "in_progress",
        "content": [],
    }
    part = {"item_id": item["id"], "output_index": index, "content_index": 0}
    yield event("response.output_item.added", output_index=index, item=item)
    yield event(
        "response.content_part.added",
        **part,
        part={"type": "output_text", "text": "", "annotations": []},
    )
    for text in chunks(answer):
        yield event("response.output_text.delta", text, **part, delta=text)
    item["content"] = [{"type": "output_text", "text": answer, "annotations": []}]
    item["status"] = "completed"
    yield event("response.output_text.done", **part, text=answer)
    yield event("response.content_part.done", **part, part=item["content"][0])
    yield event("response.output_item.done", output_index=index, item=item)
    output.append(item)
    if call:
        call_id, name, args = call
        index = len(output)
        item = {
            "id": "fc_bench",
            "type": "function_call",
            "call_id": call_id,
            "name": name,
            "arguments": "",
            "status": "in_progress",
        }
        yield event("response.output_item.added", output_index=index, item=item)
        for text in chunks(args):
            yield event(
                "response.function_call_arguments.delta",
                text,
                item_id=item["id"],
                output_index=index,
                delta=text,
            )
        item.update(arguments=args, status="completed")
        yield event(
            "response.function_call_arguments.done",
            item_id=item["id"],
            output_index=index,
            arguments=args,
        )
        yield event("response.output_item.done", output_index=index, item=item)
        output.append(item)
    output_tokens = (len(thinking) + len(answer) + (len(call[2]) if call else 0)) // 4
    yield event(
        "response.completed",
        response={
            "id": f"resp_{request_id}",
            "object": "response",
            "status": "completed",
            "output": output,
            "usage": {
                "input_tokens": input_tokens,
                "input_tokens_details": {"cached_tokens": 0},
                "output_tokens": output_tokens,
                "output_tokens_details": {"reasoning_tokens": len(thinking) // 4},
                "total_tokens": input_tokens + output_tokens,
            },
        },
    )


STREAMS = {
    "/messages": anthropic_stream,
    "/responses": responses_stream,
    "/chat/completions": chat_stream,
}


def completion(anthropic, body, answer, input_tokens):
    """A whole reply without streaming, for auxiliary requests."""
    output_tokens = len(answer) // 4
    if anthropic:
        return {
            "id": "msg_aux",
            "type": "message",
            "role": "assistant",
            "model": body.get("model"),
            "content": [{"type": "text", "text": answer}],
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
        }
    return {
        "id": "chatcmpl-aux",
        "object": "chat.completion",
        "created": 0,
        "model": body.get("model"),
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": answer},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": input_tokens,
            "completion_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        },
    }


def too_long(anthropic, tokens):
    """The provider's error for a request over the context window."""
    if anthropic:
        return {
            "type": "error",
            "error": {
                "type": "invalid_request_error",
                "message": f"prompt is too long: {tokens} tokens > "
                f"{CONTEXT_TOKENS} maximum",
            },
        }
    return {
        "error": {
            "message": "This model's maximum context length is "
            f"{CONTEXT_TOKENS} tokens. However, your messages "
            f"resulted in {tokens} tokens.",
            "type": "invalid_request_error",
            "param": "messages",
            "code": "context_length_exceeded",
        }
    }
