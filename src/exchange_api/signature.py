import hashlib
import hmac
import json
from operator import itemgetter

import aiohttp
import asyncio


async def fetch_url(url: str, header: dict, params: dict, req_method: str, signature: str) -> dict:
    params['signature'] = signature
    async with aiohttp.ClientSession() as session:
        if req_method == 'post':
            method = session.post
        elif req_method == 'get':
            method = session.get
        elif req_method == 'delete':
            method = session.delete
        async with method(url + '?' + Signature.generate_url(params), headers=header) as response:
            return json.loads(await response.text())


class Signature:
    @staticmethod
    def __order_params(data: dict) -> list[tuple[str, str]]:
        data = dict(filter(lambda el: el[1] is not None, data.items()))
        has_signature = False
        params = []
        for key, value in data.items():
            if key == 'signature':
                has_signature = True
            else:
                params.append((key, str(value)))

        params.sort(key=itemgetter(0))
        if has_signature:
            params.append(('signature', data['signature']))
        return params

    @staticmethod
    def generate_url(data: dict) -> str:
        ordered_data = Signature.__order_params(data)
        query_string = '&'.join([f"{d[0]}={d[1]}" for d in ordered_data])
        return query_string

    @staticmethod
    def _generate_signature(data: dict, secret_api) -> hmac:
        ordered_data = Signature.__order_params(data)
        query_string = '&'.join([f"{d[0]}={d[1]}" for d in ordered_data])
        m = hmac.new(secret_api.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256)
        return m

    @staticmethod
    async def generate_query(request_method: str, endpoint: str, header: list, params: list, signs: list) -> tuple:
        signatures = [str(Signature._generate_signature(param, sign).hexdigest()) for param, sign in zip(params, signs)]
        headers = [{'Content-Type': 'application/json;charset=utf-8', 'X-MBX-APIKEY': x} for x in header]
        tasks = [fetch_url(endpoint, header, param, request_method, signature) for
                 header, param, signature in zip(headers, params, signatures)]
        results = await asyncio.gather(*tasks)

        return results

