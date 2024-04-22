#! /usr/bin/env python3

# Modules requiring installation
from dateutil.parser import parse
# Built-in modules
from email import message_from_string
from email.header import decode_header, make_header
import sys
import logging
# Local modules
from ichi_function import *
import ichi_config
import ichi_macro
import ichi_warn

# Setup and disable/enable logging
logging.basicConfig(level=logging.DEBUG, 
                    format=' %(asctime)s - %(levelname)s - %(message)s')
# logging.disable(logging.CRITICAL)
logging.debug('Start of program.')

# TODO: add received as validation check
# TODO: fix failure to pull received from ICHI FAIL NEW on bypass
# TODO: account for missing message id
# TODO: account for incorrect originating email in ____
# TODO: strip output head and tail of linebreaks
# TODO: add correct commenting on pbpaste / pbcopy
# TODO: return meta-only to false and clip to true

# Global variables
raw_header_str = ''
client_name = ''
client_domains = []
evil_field_out = {}
clean_field_out = {}
final_warnings = ''
sum_statement = ''
ticket_out = ''

# The primary flow to pull the email header and analyze it
print(ichi_intro)
if ichi_config.quickness:
    print(ichi_instruct)
else:
    input(ichi_instruct)
raw_header_str = capture_email_header()
header = message_from_string(raw_header_str)
client_name = get_client_name(ichi_config.client_info)
client_domains = get_client_domains(client_name, ichi_config.client_info)
evil_field_out = create_field_output(header, 
                                        raw_header_str, 
                                        client_domains
                                        )
final_warnings = ichi_warn.get_warnings(evil_field_out)
if recip_found_check(evil_field_out) == False:
    evil_field_out = manual_get_recip(evil_field_out)
clean_field_out = sanitize_field_output(evil_field_out)
primary_meta_out = create_meta_out(clean_field_out)
printable_meta = str_from_lst(primary_meta_out)
sum_statement = ichi_macro.get_sum_state(clean_field_out)
ticket_out = ichi_macro.get_full_macro(sum_statement, 
                                printable_meta, 
                                raw_header_str,
                                client_name,
                                ichi_config.personal_info
                                )

# Print final outputs determined in config
if ichi_config.meta_only:
    final_output = printable_meta
else:
    final_output = ticket_out
    
if ichi_config.clip_output:
    pbcopy(final_output)
    print(out_heading)
    print(final_output)
else:
    print(out_heading)
    print(final_output)

if final_warnings and ichi_config.print_warnings:
    print(final_warnings)

sys.exit()