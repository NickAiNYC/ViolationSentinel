"""
Example: Integrating structured logging with NYC Data Client.

This example shows how to use the production-grade logging system
with the NYC Data Client for comprehensive observability.
"""

import asyncio
import uuid
from infrastructure import (
    setup_logging,
    get_logger,
    set_request_context,
    clear_request_context,
    log_execution_time,
    log_exceptions,
)
from api.nyc_data_client import NYCDataClient


# Initialize logging at application startup
setup_logging(log_level='INFO', environment='development')

# Get logger for this module
logger = get_logger(__name__)


@log_execution_time
@log_exceptions
async def fetch_property_violations(bbl: str, request_id: str):
    """
    Fetch violations for a property with full logging.
    
    This function demonstrates:
    - Request context tracking (correlation IDs)
    - Automatic execution time logging
    - Automatic exception logging
    - Structured logging with metadata
    """
    # Set request context for tracing
    set_request_context(request_id=request_id, user_id="system")
    
    logger.info(f"Starting violation fetch for BBL {bbl}")
    
    try:
        async with NYCDataClient() as client:
            # Fetch DOB violations
            logger.debug(f"Fetching DOB violations for {bbl}")
            dob_violations = await client.get_dob_violations(bbl, limit=10)
            logger.info(
                f"DOB violations retrieved",
                extra={
                    'bbl': bbl,
                    'count': len(dob_violations),
                    'data_type': 'dob_violations',
                }
            )
            
            # Fetch HPD violations
            logger.debug(f"Fetching HPD violations for {bbl}")
            hpd_violations = await client.get_hpd_violations(bbl, limit=10)
            logger.info(
                f"HPD violations retrieved",
                extra={
                    'bbl': bbl,
                    'count': len(hpd_violations),
                    'data_type': 'hpd_violations',
                }
            )
            
            # Get cache statistics
            stats = client.get_stats()
            logger.info(
                "Client statistics",
                extra={
                    'cache_hit_rate': stats['cache_hit_rate'],
                    'total_requests': stats['requests'],
                    'errors': stats['errors'],
                }
            )
            
            return {
                'bbl': bbl,
                'dob_violations': len(dob_violations),
                'hpd_violations': len(hpd_violations),
            }
    
    except Exception as e:
        logger.error(
            f"Failed to fetch violations for {bbl}",
            extra={
                'bbl': bbl,
                'error_type': type(e).__name__,
            },
            exc_info=True
        )
        raise
    
    finally:
        # Clear request context
        clear_request_context()


@log_execution_time
async def batch_process_properties(bbls: list):
    """Process multiple properties with logging."""
    request_id = str(uuid.uuid4())
    set_request_context(request_id=request_id)
    
    logger.info(
        "Starting batch property processing",
        extra={
            'property_count': len(bbls),
            'batch_id': request_id,
        }
    )
    
    results = []
    for bbl in bbls:
        # Each property gets its own sub-request ID
        sub_request_id = f"{request_id}-{bbl}"
        try:
            result = await fetch_property_violations(bbl, sub_request_id)
            results.append(result)
        except Exception as e:
            logger.warning(
                f"Failed to process property {bbl}, continuing with others",
                extra={'bbl': bbl, 'error': str(e)}
            )
    
    logger.info(
        "Batch processing completed",
        extra={
            'total_properties': len(bbls),
            'successful': len(results),
            'failed': len(bbls) - len(results),
        }
    )
    
    clear_request_context()
    return results


async def main():
    """Main example demonstrating logging integration."""
    logger.info("Application started")
    
    # Example 1: Single property with request tracking
    logger.info("=" * 70)
    logger.info("Example 1: Single Property Fetch")
    logger.info("=" * 70)
    
    request_id = str(uuid.uuid4())
    try:
        result = await fetch_property_violations("3012650001", request_id)
        logger.info(f"Result: {result}")
    except Exception:
        logger.error("Single property fetch failed")
    
    # Example 2: Batch processing
    logger.info("\n" + "=" * 70)
    logger.info("Example 2: Batch Processing")
    logger.info("=" * 70)
    
    bbls = ["3012650001", "1012650001", "2012650001"]
    results = await batch_process_properties(bbls)
    logger.info(f"Batch results: {len(results)} properties processed")
    
    # Example 3: Different log levels
    logger.info("\n" + "=" * 70)
    logger.info("Example 3: Log Levels")
    logger.info("=" * 70)
    
    logger.debug("This is a DEBUG message (detailed information)")
    logger.info("This is an INFO message (general information)")
    logger.warning("This is a WARNING message (something to watch)")
    logger.error("This is an ERROR message (something went wrong)")
    
    # Example 4: Structured metadata
    logger.info("\n" + "=" * 70)
    logger.info("Example 4: Structured Logging")
    logger.info("=" * 70)
    
    logger.info(
        "Property analysis completed",
        extra={
            'analysis_type': 'violation_check',
            'total_properties': 3,
            'high_risk_count': 1,
            'medium_risk_count': 1,
            'low_risk_count': 1,
            'avg_violations': 15.7,
        }
    )
    
    logger.info("Application completed successfully")


if __name__ == "__main__":
    asyncio.run(main())
