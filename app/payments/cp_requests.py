import base64
from typing import Literal
from tenacity import retry, stop_after_attempt, wait_exponential
from aiohttp import ClientSession
from app.util.logger import logger
from app.util.config import config
from app.payments.util import process_cloudpayment_log


auth_string = f'{config.CLOUDPAYMENTS_PUBLIC_ID}:{config.CLOUDPAYMENTS_API_SECRET}'
auth_header = f'Basic {base64.b64encode(auth_string.encode()).decode()}'
cloudpayments_headers = {
    'Content-Type': 'application/json',
    'Authorization': auth_header
}

MAX_RETRIES = 3

@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
async def request_cp_extract_model(url: str, payload: dict) -> dict:
    try:
        async with ClientSession() as session:
            async with session.post(url, json=payload, headers=cloudpayments_headers) as response:
                data = await response.json()

                if response.status == 200 and data.get('Success'):
                    return data.get('Model', {})
                else:
                    raise ValueError(f'Invalid response. status: {response.status}, success: {data.get('Success')}')
    except Exception as e:
        logger.error(f'CloudPayments request failed after {MAX_RETRIES} attempts:\n{e}')
        return {}


# SUBSCRIPTIONS

async def cp_find_subscription(id: str) -> dict | None:
    url = 'https://api.cloudpayments.ru/subscriptions/get'
    payload = {'Id': id}
    sub = await request_cp_extract_model(url, payload)
    process_cloudpayment_log('details', sub)
    if sub.get('Status'):
        return sub
    else:
        return None


async def cp_get_subscription_status(id: str) -> Literal['Active', 'Cancelled', 'PastDue', 'Rejected', 'Expired'] | None:
    sub = await cp_find_subscription(id)
    return (sub or {}).get('Status')


async def cp_get_user_subscriptions(user_id: int | str) -> list[dict]:
    url = 'https://api.cloudpayments.ru/subscriptions/find'
    payload = {'AccountId': str(user_id)}
    subscriptions: list[dict] = await request_cp_extract_model(url, payload)  # type: ignore
    for sub in subscriptions:
        process_cloudpayment_log('details', sub)
    return subscriptions


async def cp_cancel_subscription(id: str):
    if id:
        url = 'https://api.cloudpayments.ru/subscriptions/cancel'
        payload = {'Id': id}
        response = await request_cp_extract_model(url, payload)
        process_cloudpayment_log('details', response)


async def cp_cancel_colateral_subscriptions(subscriptions: list[dict], subscription_id: str | None = None):
    sub_ids = [sub.get('Id') for sub in subscriptions]
    if subscription_id and subscription_id in sub_ids:
        for id in sub_ids:
            if id != subscription_id and isinstance(id, str):
                await cp_cancel_subscription(id)
    else:
        more_used_subscriptions = sorted(subscriptions, key=lambda x: x.get('SuccessfulTransactionsNumber', 0), reverse=True)
        for sub in more_used_subscriptions[1:]:
            sub_id = sub.get('Id')
            if isinstance(sub_id, str):
                await cp_cancel_subscription(sub_id)
    

