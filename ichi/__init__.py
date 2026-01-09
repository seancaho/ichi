#! /usr/bin/env python3

from .input import intro, instruct, mk_heading, mk_highlight, pbcopy, \
    capture_input, client_detection, get_client_domains, email_from_file
from .extract import get_header_text, get_body, get_attachments, \
    get_images, get_anchors, build_hop_data
# from .enrich import 
# from .analyze import
from .format import create_field_output, sanitize_field_output
from .flags import get_warnings
from .macro import get_sum_state, get_full_macro, create_meta_out
from .console import console
from .cli import loader, print_loop
# __all__ = ["extract"] define api...