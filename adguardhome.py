#!/usr/bin/env python3

"""
Run without any argument to use default settings hard coded in the script.

Run `python adguardhome.py -h` to see all available options.
"""

from pathlib import Path
import shutil
import tempfile
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
        self.extra_dns = self.load_extra_dns_conf(Path(args.extra_dns_file))
        self.records = set()

    def load_extra_dns_conf(self, extra_dns_file: Path):
        if not extra_dns_file.exists():
            return {}

        extra_dns = {}
        with open(extra_dns_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line.startswith("[/"):
                    print(f"invalid extra dns line, invalid start: {line}")
                    continue

                start = line.find("/]")
                if start == -1:
                    print(f"invalid extra dns line, no domain format end: {line}")
                    continue

                domain = line[2:start]
                extra_dns[domain] = line
                # print(f"loading extra dns: {domain}")

        return extra_dns

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
                if domain not in self.extra_dns:
                    self.records.add(domain)

    def fetch_and_process(self):
        for url in self.config_urls:
            self.fetch_and_process_one(url)

        if len(self.records) < EXPECTED_MIN_LENGTH:
            raise ValueError(
                f"Something may be wrong, only {len(self.records)} records found, expected at least {EXPECTED_MIN_LENGTH}."
            )

    def save(self, output):
        # Write to tmp file first, then rename it to output file.
        tmp_file = None
        with tempfile.NamedTemporaryFile(
            prefix=f"{output}.", delete=False, mode="w", dir="."
        ) as f:
            tmp_file = f.name

            f.write(self.trusted_dns)
            f.write("\n")

            for _, extra_dns_line in self.extra_dns.items():
                f.write(f"{extra_dns_line}\n")

            for domain in self.records:
                f.write(f"[/{domain}/]{self.china_dns}\n")

        # Backup if exists.
        if Path(output).exists():
            shutil.copy2(output, output + ".bak")

        Path(tmp_file).rename(output)
        Path(output).chmod(0o644)

    def run(self, output):
        self.fetch_and_process()
        self.save(output)


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
