#! /usr/bin/env python3

# Modules requiring installation

# Built-in modules
from email import message_from_string
from email.header import decode_header, make_header
import sys
import logging
# Local modules
import ichi_function as ichi_fn
import ichi_config
import ichi_macro
import ichi_warn

# Setup and disable/enable logging
logging.basicConfig(level=logging.DEBUG, 
                    format=' %(asctime)s - %(levelname)s - %(message)s')
logging.disable(logging.CRITICAL)
logging.debug('Start of program.')

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
def main():

    print(ichi_fn.ichi_intro)

    if ichi_config.quickness:
        print(ichi_fn.ichi_instruct)
    else:
        input(ichi_fn.ichi_instruct)
    raw_header_str = ichi_fn.capture_email_header()
    header = message_from_string(raw_header_str)
    client_name = ichi_fn.get_client_name(ichi_config.client_info)
    client_domains = ichi_fn.get_client_domains(client_name, 
                                            ichi_config.client_info)
    evil_field_out = ichi_fn.create_field_output(header, 
                                            raw_header_str, 
                                            client_domains
                                            )
    final_warnings = ichi_warn.get_warnings(evil_field_out)
    if ichi_fn.recip_found_check(evil_field_out) == False:
        evil_field_out = ichi_fn.manual_get_recip(evil_field_out)
    clean_field_out = ichi_fn.sanitize_field_output(evil_field_out)

    # debugging
    print("\nknown_recip_str: ")
    print(clean_field_out['known_recip_str'])
    print("\nknown_recip_lst: ")
    print(clean_field_out['known_recip_lst'])
    print("\nknown_recip_eml_lst: ")
    print(clean_field_out['known_recip_eml_lst'])
    print("\nknown_recip_eml_str: ")
    print(clean_field_out['known_recip_eml_str'])
#    sys.exit()
    # debugging

    primary_meta_out = ichi_fn.create_meta_out(clean_field_out)
    printable_meta = ichi_fn.str_from_lst(primary_meta_out)
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
        ichi_fn.pbcopy(final_output)
        print(ichi_fn.out_heading)
        print(final_output)
    else:
        print(ichi_fn.out_heading)
        print(final_output)

    if final_warnings and ichi_config.print_warnings:
        print(final_warnings)

    sys.exit()

if __name__ == "__main__":
    main()