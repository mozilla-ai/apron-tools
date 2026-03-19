"""Salesforce provider.

API docs: https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/
"""

from .tools import (
    salesforce_create_record,
    salesforce_explore_org,
    salesforce_get_record,
    salesforce_query_records,
    salesforce_search_records,
    salesforce_update_record,
)

__all__ = [
    "salesforce_create_record",
    "salesforce_explore_org",
    "salesforce_get_record",
    "salesforce_query_records",
    "salesforce_search_records",
    "salesforce_update_record",
]
