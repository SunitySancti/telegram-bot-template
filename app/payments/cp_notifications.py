from functools import wraps
from fastapi import APIRouter, Request
from app.db.dao import DAO
from app.util.logger import logger
from app.payments.util import process_cloudpayment_log


cloudpayments_router = APIRouter()

def process_cloudpayment_notification(name: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            payload = dict(await request.form())

            try:
                results = await DAO.Payment.save(payload)
                process_cloudpayment_log(name, payload, results)

                await func(request, *args, **kwargs)
                return {'code': 0}

            except Exception as e:
                logger.exception(f'Error in cloudpayment "{name}" notification handler:\n{e}')
                return {'code': 0}
                
        return wrapper
    return decorator


@cloudpayments_router.post('/check')
async def cloudpayments_webhook_check(request: Request):
    payload = dict(await request.form())
    # test_mode = False
    try:
        # test_mode = payload.get('TestMode') == '1'
        process_cloudpayment_log('check', payload)

    finally:
        # if test_mode:
        #     return {'code': 1}
        # else:
            return {'code': 0}


@cloudpayments_router.post('/pay')
@process_cloudpayment_notification('pay')
async def cloudpayments_webhook_pay(request: Request):
    pass


@cloudpayments_router.post('/fail')
@process_cloudpayment_notification('fail')
async def cloudpayments_webhook_fail(request: Request):
    pass


@cloudpayments_router.post('/recurrent')
@process_cloudpayment_notification('recurrent')
async def cloudpayments_webhook_recurrent(request: Request):
    pass


@cloudpayments_router.post('/cancel')
@process_cloudpayment_notification('cancel')
async def cloudpayments_webhook_cancel(request: Request):
    pass

