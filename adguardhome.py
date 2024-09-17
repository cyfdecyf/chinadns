#!/usr/bin/env python

"""
Run without any argument to use default settings hard coded in the script.

Run `python adguardhome.py -h` to see all available options.
"""

from pathlib import Path
import urllib.request


DOWNLOAD_CONFIG_LIST = [
    "https://raw.githubusercontent.com/felixonmars/dnsmasq-china-list/master/accelerated-domains.china.conf",
    "https://raw.githubusercontent.com/felixonmars/dnsmasq-china-list/master/apple.china.conf",
]

CHINA_DNS = ["223.5.5.5", "223.6.6.6"]

# Each line is a trusted DNS server.
TRUSTED_DNS = ["tls://8.8.8.8", "tls://8.8.4.4"]

EXTRA_DNS_FILE = "extra.conf"

# If the length of config is less than this value, something maybe wrong.
EXPECTED_MIN_LENGTH = 70000


class ChinaDnsAdguardHome:
    def __init__(
        self,
        args,
    ) -> None:
        self.config_urls = args.config_urls
        self.china_dns = " ".join(args.china_dns)
        self.trusted_dns = "\n".join(args.trusted_dns)
        self.extra_dns_file = args.extra_dns_file
        self.records = set()

    def fetch_and_process_one(self, url: str):
        with urllib.request.urlopen(url) as response:
            print(f"downloading {url}")
            data = response.read().decode("utf-8")
            for line in data.splitlines():
                line = line.strip()
                # lines starting with # are comments
                if not line.startswith("server="):
                    continue

                first_slash = line.find("/")
                if first_slash == -1:
                    print(f"invalid line: {line}")
                    continue
                second_slash = line.find("/", first_slash + 1)
                if second_slash == -1:
                    print(f"invalid line: {line}")
                    continue

                domain = line[first_slash + 1 : second_slash]
                self.records.add(domain)

    def fetch_and_process(self):
        for url in self.config_urls:
            self.fetch_and_process_one(url)

        if len(self.records) < EXPECTED_MIN_LENGTH:
            raise ValueError(
                f"Something may be wrong, only {len(self.records)} records found, expected at least {EXPECTED_MIN_LENGTH}."
            )

    def write(self, output):
        with open(output, "w") as f:
            f.write(self.trusted_dns)
            f.write("\n")
            for domain in self.records:
                f.write(f"[/{domain}/]{self.china_dns}\n")

            extra_dns_file = Path(self.extra_dns_file)
            if extra_dns_file.exists():
                with open(extra_dns_file, "r") as exf:
                    f.write(exf.read())

    def run(self, output):
        self.fetch_and_process()
        self.write(output)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        "--config-urls",
        nargs="*",
        help="Config URLs to download",
        type=list[str],
        default=DOWNLOAD_CONFIG_LIST,
    )
    parser.add_argument(
        "-d",
        "--china-dns",
        nargs="*",
        help="China DNS Servers",
        type=list[str],
        default=CHINA_DNS,
    )
    parser.add_argument(
        "-t",
        "--trusted-dns",
        nargs="*",
        help="Trusted DNS Servers",
        type=list[str],
        default=TRUSTED_DNS,
    )
    parser.add_argument(
        "-e",
        "--extra-dns-file",
        help="Extra DNS File",
        type=str,
        default=EXTRA_DNS_FILE,
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output file",
        type=str,
        default="china-dns-adguardhome.conf",
    )

    args = parser.parse_args()

    cda = ChinaDnsAdguardHome(args)
    cda.run(args.output)
