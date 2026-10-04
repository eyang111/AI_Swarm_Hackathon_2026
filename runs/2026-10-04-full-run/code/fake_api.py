"""Offline stand-in for the Anthropic HTTP API, for testing the real backend code path (SI_FAKE_API=1).

It serves POST /v1/messages (SSE stream), POST /v1/messages/batches, GET .../batches/{id}, GET .../results (JSONL)
through an httpx MockTransport, so the SDK's request building and response parsing run for real. The content of each
response comes from the job's mock function (registered by llm.py, keyed by the user text). Requests whose text
contains an id from SI_MOCK_REFUSE_IDS get stop_reason "refusal". Every request body is validated for the
parameters the pipeline relies on.
"""
import json, os, uuid
import httpx2 as httpx

REFUSE = set(filter(None, os.environ.get('SI_MOCK_REFUSE_IDS', '').split(',')))
SEEN = []


def _check(body):
    assert body['model'] in ('claude-sonnet-5-5', 'claude-opus-5-5'), body['model']
    assert body['output_config']['format']['type'] == 'json_schema'
    assert body['output_config']['effort'] in ('low', 'medium')
    assert body['system'][0]['cache_control'] == {'type': 'ephemeral'}
    assert 'thinking' not in body and 'temperature' not in body
    SEEN.append(dict(model=body['model'], stream=body.get('stream'), fallbacks=body.get('fallbacks'), max_tokens=body['max_tokens']))


def _answer(registry, body):
    user = body['messages'][0]['content']
    if any(r in user for r in REFUSE):
        return '', 'refusal'
    data = registry[user]()
    return json.dumps(data), 'end_turn'


def _message(model, text, stop):
    return {'id': 'msg_' + uuid.uuid4().hex[:12], 'type': 'message', 'role': 'assistant', 'model': model,
            'content': [{'type': 'text', 'text': text}] if text else [], 'stop_reason': stop, 'stop_sequence': None,
            'stop_details': {'type': 'refusal', 'category': 'cyber', 'explanation': 'fake'} if stop == 'refusal' else None,
            'usage': {'input_tokens': 1000, 'output_tokens': max(1, len(text) // 4), 'cache_read_input_tokens': 500,
                      'cache_creation_input_tokens': 0}}


def _sse(msg):
    ev = []
    start = dict(msg, content=[], stop_reason=None, usage=dict(msg['usage'], output_tokens=1))
    ev.append(('message_start', {'type': 'message_start', 'message': start}))
    if msg['content']:
        ev.append(('content_block_start', {'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text', 'text': ''}}))
        ev.append(('content_block_delta', {'type': 'content_block_delta', 'index': 0,
                                           'delta': {'type': 'text_delta', 'text': msg['content'][0]['text']}}))
        ev.append(('content_block_stop', {'type': 'content_block_stop', 'index': 0}))
    ev.append(('message_delta', {'type': 'message_delta', 'delta': {'stop_reason': msg['stop_reason'], 'stop_sequence': None,
                                                                     'stop_details': msg['stop_details']},
                                 'usage': {'output_tokens': msg['usage']['output_tokens']}}))
    ev.append(('message_stop', {'type': 'message_stop'}))
    return ''.join(f'event: {e}\ndata: {json.dumps(d)}\n\n' for e, d in ev).encode()


def make_client(registry):
    import anthropic
    batches = {}

    def handler(req: httpx.Request):
        path = req.url.path
        if req.method == 'POST' and path == '/v1/messages':
            body = json.loads(req.content)
            _check(body)
            text, stop = _answer(registry, body)
            return httpx.Response(200, content=_sse(_message(body['model'], text, stop)),
                                  headers={'content-type': 'text/event-stream'})
        if req.method == 'POST' and path == '/v1/messages/batches':
            body = json.loads(req.content)
            bid = 'msgbatch_' + uuid.uuid4().hex[:10]
            res = []
            for r in body['requests']:
                _check(r['params'])
                assert 'fallbacks' not in r['params']
                text, stop = _answer(registry, r['params'])
                res.append({'custom_id': r['custom_id'], 'result': {'type': 'succeeded', 'message': _message(r['params']['model'], text, stop)}})
            batches[bid] = res
            return httpx.Response(200, json=_batch(bid, 'in_progress', len(res)))
        if req.method == 'GET' and path.startswith('/v1/messages/batches/'):
            bid = path.split('/')[4]
            if path.endswith('/results'):
                return httpx.Response(200, content='\n'.join(json.dumps(r) for r in batches[bid]).encode(),
                                      headers={'content-type': 'application/binary'})
            return httpx.Response(200, json=_batch(bid, 'ended', len(batches[bid])))
        return httpx.Response(404, json={'type': 'error', 'error': {'type': 'not_found_error', 'message': path}})

    return anthropic.Anthropic(api_key='fake', base_url='https://fake.local',
                               http_client=httpx.Client(transport=httpx.MockTransport(handler)))


def _batch(bid, status, n):
    return {'id': bid, 'type': 'message_batch', 'processing_status': status,
            'request_counts': {'processing': 0 if status == 'ended' else n, 'succeeded': n if status == 'ended' else 0,
                               'errored': 0, 'canceled': 0, 'expired': 0},
            'ended_at': None, 'created_at': '2026-10-04T00:00:00Z', 'expires_at': '2026-10-05T00:00:00Z',
            'archived_at': None, 'cancel_initiated_at': None,
            'results_url': f'https://fake.local/v1/messages/batches/{bid}/results'}
