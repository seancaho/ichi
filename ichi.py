#! /usr/bin/env python3

# Modules requiring installation

# Built-in modules
from email import message_from_string
from email.header import decode_header, make_header
import sys
import logging
import argparse
# Local modules
import functions as ichi_fn
import config
import macro
import flags

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

parser = argparse.ArgumentParser(
                    prog='IchiScript',
                    description='The swiss-army-knife of eml analysis.')
parser.add_argument('cmd',
                    help='The primary function you want to use.',
                    type=str, 
                    choices={"analyze", "phish", "setup", "report"},
                    default='phish')
parser.add_argument("-i", "--input", 
                           help="Specify the full path of the eml file to " \
                           "analyze, 'clipboard', or 'working' for the working " \
                            "directory. Defaults to the most recently created " \
                                "eml in your working directory.",
                           type=str)
parser.add_argument("-c", "--client",
                            help="Manually specify the client to bypass automated check.",
                            choices=list(config.client_info),
                            type=str)
args = parser.parse_args()

# The primary flow to pull the email header and analyze it
def main():

    print(ichi_fn.ichi_intro)

    #if config.quickness:
    #    print(ichi_fn.ichi_instruct)
    #else:
    #    input(ichi_fn.ichi_instruct)
    print(ichi_fn.ichi_instruct)
    # TODO: reset to normal or remove slowness

    email_obj = ichi_fn.capture_input(
        args, config.working_directory)

    new_header = ''
    # TODO: refactor to make this unnecessary
    for v,s in email_obj.items():
        new_header += v + ' ' + s + '\n'
    raw_header_str = new_header

    print(ichi_fn.mk_heading("CLIENT SELECTION"))

    client_name = ichi_fn.client_detection(config.client_info,
                                args.client, email_obj)

    client_domains = ichi_fn.get_client_domains(client_name, 
                                            config.client_info)
    
    #TODO: figure out where simplify_string needs called and implement

    evil_field_out = ichi_fn.create_field_output(email_obj, 
                                            raw_header_str, 
                                            client_domains
                                            )
    final_warnings = flags.get_warnings(evil_field_out)

    clean_field_out = ichi_fn.sanitize_field_output(evil_field_out)
    primary_meta_out = ichi_fn.create_meta_out(clean_field_out)
    printable_meta = "\n".join(primary_meta_out)
    sum_statement = macro.get_sum_state(clean_field_out, config.truncate_summary)
    ticket_out = macro.get_full_macro(sum_statement, 
                                    printable_meta, 
                                    raw_header_str,
                                    config.personal_info
                                    )

    # Print final outputs determined in config
    if config.meta_only:
        final_output = printable_meta
    else:
        final_output = ticket_out
        
    if config.clip_output:
        ichi_fn.pbcopy(final_output)

    print(ichi_fn.mk_heading("OUTPUT"))
    print(final_output) #TODO: option to turn off printing output

    if final_warnings and config.print_warnings:
        print(ichi_fn.mk_heading("WARNINGS"))
        print(final_warnings)

    sys.exit()

if __name__ == "__main__":
    main()