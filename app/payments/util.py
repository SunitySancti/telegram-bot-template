from typing import Any, Optional
from app.util.logger import logger, logger_block_header, logger_block_body, logger_block_footer


loggers = {
    'details': logger.debug,
    # 'create_link': logger.debug,
    'create_subscription': logger.debug,
    'check': logger.info,
    'pay': logger.info,
    'fail': logger.warning,
    'recurrent': logger.warning,
    'cancel': logger.warning,
}

def process_cloudpayment_log(case: str, payload: dict[str, Any], results: Optional[dict[str, bool]] = None):
    try:
        k = max([len(key) for key in payload.keys()])
        if case == 'check':
            body = 'Status: ' + payload.get('Status', 'Unidentified')
        else:
            body = '\n'.join([f'{key}:{(k - len(key)) * " "} {val}' for key, val in payload.items()])

        loggers[case](logger_block_header(case, double=True))
        loggers[case](logger_block_body(body, double=True))
        if results:
            stringified_results = '\n'.join([f'• {key}: {str(value)}' for key, value in results.items()])
            loggers[case](logger_block_body('__________________\nPROCESSING RESULTS\n' + stringified_results, double=True))
        loggers[case](logger_block_footer(double=True))
    except:
        pass
