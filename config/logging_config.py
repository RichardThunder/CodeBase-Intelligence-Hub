"""Logging configuration and callback handlers for LLM API requests."""

import logging
import json
from datetime import datetime
from typing import Any, Dict, List
from langchain_core.callbacks import BaseCallbackHandler


# Configure Python logging
def setup_logging():
    """Set up logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),  # Console output
            logging.FileHandler('api_requests.log'),  # File output
        ]
    )


class LLMRequestLogger(BaseCallbackHandler):
    """Custom callback handler to log LLM API requests."""

    def __init__(self):
        """Initialize the logger."""
        self.logger = logging.getLogger('LLM_Requests')

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        **kwargs: Any,
    ) -> None:
        """Log the start of an LLM call with request details.

        Args:
            serialized: Serialized LLM information
            prompts: List of prompts sent to the LLM
            **kwargs: Additional arguments
        """
        request_info = {
            'timestamp': datetime.now().isoformat(),
            'event': 'llm_request_start',
            'model': serialized.get('kwargs', {}).get('model', 'unknown'),
            'prompts_count': len(prompts),
            'prompts': prompts,
            'serialized_info': {
                'id': serialized.get('id', []),
                'kwargs': {
                    k: v for k, v in serialized.get('kwargs', {}).items()
                    if k not in ['api_key']  # Don't log sensitive data
                }
            }
        }

        self.logger.info(
            f"LLM API Request:\n{json.dumps(request_info, ensure_ascii=False, indent=2)}"
        )

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        """Log the end of an LLM call with response info.

        Args:
            response: LLM response
            **kwargs: Additional arguments
        """
        response_info = {
            'timestamp': datetime.now().isoformat(),
            'event': 'llm_request_end',
            'generations_count': len(response.generations) if hasattr(response, 'generations') else 0,
        }

        self.logger.info(
            f"LLM API Response:\n{json.dumps(response_info, ensure_ascii=False, indent=2)}"
        )

    def on_llm_error(self, error: Exception, **kwargs: Any) -> None:
        """Log LLM errors.

        Args:
            error: Exception that occurred
            **kwargs: Additional arguments
        """
        error_info = {
            'timestamp': datetime.now().isoformat(),
            'event': 'llm_request_error',
            'error_type': type(error).__name__,
            'error_message': str(error),
        }

        self.logger.error(
            f"LLM API Error:\n{json.dumps(error_info, ensure_ascii=False, indent=2)}"
        )


# Create a global logger instance
logger = logging.getLogger(__name__)
