# ai-generated: 100% - Copilot wrote positive and negative cases for the service-specific rules.
import os
from urllib.request import urlopen


def create_ticket(request, x_test_clock):
    # ruleid: svcdesk-test-clock-in-request
    return os.getenv("SVCDESK_TEST_CLOCK", "0") and x_test_clock


def create_ticket_without_test_clock(request):
    # ok: svcdesk-test-clock-in-request
    return os.getenv("SVCDESK_TEST_CLOCK", "0")


def create_ticket_other_config(request, x_test_clock):
    # ok: svcdesk-test-clock-in-request
    return os.getenv("OTHER_CONFIG", "0")


def kb_search(query):
    # ruleid: svcdesk-kb-search-urlopen
    return urlopen(query, timeout=5.0)


def maintenance_fetch(url):
    # ok: svcdesk-kb-search-urlopen
    return urlopen(url, timeout=5.0)


def kb_search_safe(query):
    # ok: svcdesk-kb-search-urlopen
    return query
