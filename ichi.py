#! /usr/bin/env python3

# Modules requiring installation

# Built-in modules
from email import message_from_string
from email.header import decode_header, make_header
import sys
import logging
import argparse
import pprint

# Local modules
import ichi
import config



# Setup and disable/enable logging
logging.basicConfig(level=logging.DEBUG, 
                    format=' %(asctime)s - %(levelname)s - %(message)s')
logging.disable(logging.CRITICAL)
logging.debug('Start of program.')



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



def phish():

    print(ichi.intro)
    print(ichi.mk_heading("ICHI START"))
    print(ichi.instruct)

    email_obj, header_raw = ichi.capture_input(
        args, config.working_directory)

    print(ichi.mk_heading("CLIENT SELECTION"))

    client_name = ichi.client_detection(config.client_info,
                                args.client, email_obj)

    client_domains = ichi.get_client_domains(client_name, 
                                            config.client_info)
    
    evil_field_out = ichi.create_field_output(email_obj, 
                                            client_domains
                                            )
        
    # create warnings from basic info parsed
    flags = ichi.get_warnings(evil_field_out)
    printable_flags = "\n".join(flags)

    # create final data and build macro
    clean_field_out = ichi.sanitize_field_output(evil_field_out)

    primary_meta_out = ichi.create_meta_out(clean_field_out)

    printable_meta = "\n".join(primary_meta_out)
    sum_statement = ichi.get_sum_state(clean_field_out, config.truncate_summary)
    ticket_out = ichi.get_full_macro(sum_statement, 
                                    printable_meta, 
                                    header_raw,
                                    config.personal_info
                                    )

    # Set output to match config
    if config.meta_only:
        final_output = printable_meta
    else:
        final_output = ticket_out

    # Copy output to clipboard according to config    
    if config.clip_output:
        ichi.pbcopy(final_output)

    # Print output to cli according to config
    print(ichi.mk_heading("OUTPUT"))
    if config.print_output:
        print(final_output)

        if printable_flags and config.print_warnings:
            print(ichi.mk_heading("WARNINGS"))
            print(printable_flags)
    else:
        print(ichi.mk_highlight("Script ran successfully."))

    sys.exit()

def analyze():

    print(ichi.intro)
    print(ichi.mk_heading("ICHI START"))
    print(ichi.instruct)

    email_obj, header_raw = ichi.capture_input(
        args, config.working_directory)

    print(ichi.mk_heading("CLIENT SELECTION"))

    client_name = ichi.client_detection(config.client_info,
                                args.client, email_obj)

    client_domains = ichi.get_client_domains(client_name, 
                                            config.client_info)
    
    evil_field_out = ichi.create_field_output(email_obj, 
                                            client_domains
                                            )
    
    attachments = ichi.get_attachments(email_obj)

    pprint.pprint(attachments)


def main():
    if args.cmd == "phish":
        phish()
    elif args.cmd == "analyze":
        analyze()


if __name__ == "__main__":
    main()