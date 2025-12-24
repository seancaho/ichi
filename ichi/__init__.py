#! /usr/bin/env python3

from .input import intro, instruct, mk_heading, mk_highlight, pbcopy, \
    capture_input, client_detection, get_client_domains
from .extract import get_attachments
# from .enrich import 
# from .analyze import
from .format import create_field_output, sanitize_field_output
from .flags import get_warnings
from .macro import get_sum_state, get_full_macro, create_meta_out
# __all__ = ["extract"] define api...