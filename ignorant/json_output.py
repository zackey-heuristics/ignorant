"""
This module is responsible for the CLI interface of the Ignorant tool.

Usage:
    python -m ignorant.json_output [PHONE_NUMBER_WITH_COUNTRY_CODE] [-o OUTPUT] [-T TIMEOUT]

Example:
    python -m ignorant.json_output +33644637111
    python -m ignorant.json_output +33644637111 -o output.json

Note:
    The phone number must be in international format (e.g. +33644637111)
    The timeout is in seconds and is optional (default is 10)
"""
import argparse
import datetime
import json
import pathlib
import sys
from tabnanny import check
import time

import httpx
import phonenumbers
import trio

from ignorant.core import check_update, import_submodules, get_functions, launch_module


def validate_phone_number(phone_number_string) -> bool:
    """
    Validate a phone number string
    
    Args:
        phone_number_string (str): Phone number string
    
    Returns:
        is_valid (bool): Whether the phone number is valid
            True: Phone number is valid
            False: Phone number is invalid
    """
    try:
        # parse the phone number string
        phone_number = phonenumbers.parse(phone_number_string, None)
    except phonenumbers.phonenumberutil.NumberParseException as e:
        print(f"Parse error: {e}", file=sys.stderr)
        return False

    # Theoretical possibility check (e.g., digit count, etc.)
    if not phonenumbers.is_possible_number(phone_number):
        print("This is not a valid phone number format.", file=sys.stderr)
        return False

    # Real-world possibility check (e.g., is it in use?)
    if not phonenumbers.is_valid_number(phone_number):
        print("This is not a valid phone number.", file=sys.stderr)
        return False
    else:
        return True


async def maincore():
    parser = argparse.ArgumentParser(description="Ignorant CLI")
    parser.add_argument("phone_number_with_country_code",
                        metavar='PHONE_NUMBER_WITH_COUNTRY_CODE',
                        help="Phone number with country code (e.g. +442083661177)")
    parser.add_argument("-o", "--output",
                        help="Output file path")
    parser.add_argument("-T","--timeout", type=int , default=10, required=False,dest="timeout",
                    help="Set max timeout value (default 10)")
    args = parser.parse_args()
    
    if not validate_phone_number(args.phone_number_with_country_code):
        print("Invalid phone number. Exiting.", file=sys.stderr)
        sys.exit(1)
    
    country_code = phonenumbers.parse(args.phone_number_with_country_code).country_code
    phone_number = phonenumbers.parse(args.phone_number_with_country_code).national_number
    output = args.output
    
    check_update()
    
    modules = import_submodules("ignorant.modules")
    websites = get_functions(modules,args)
    
    # get timeout
    timeout = args.timeout
    
    # start time
    start_time = time.time()
    
    # define the async client
    client = httpx.AsyncClient(timeout=timeout)
    
    # launch the modules
    out = []
    async with trio.open_nursery() as nursery:
        for website in websites:
            nursery.start_soon(launch_module, website, phone_number, country_code, client, out)

    # sort by modules names
    out = sorted(out, key=lambda x: x["name"])
    
    # close the client
    await client.aclose()
    
    # print the results for json output
    if output:
        with open(output, "w") as f:
            json.dump(out, f, indent=4, ensure_ascii=False)
        print(f"{pathlib.Path(output).resolve()}")
    else:
        print(json.dumps(out, indent=4, ensure_ascii=False))


def main():
    trio.run(maincore)
    
    
if __name__ == "__main__":
    main()
