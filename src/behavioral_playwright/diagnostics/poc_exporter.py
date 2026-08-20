"""
Automated Exploit Proof-of-Concept exporter for replication of intercepted security test requests.
"""

import logging
import pathlib
import time
from typing import Dict, Optional

logger = logging.getLogger("BehavioralAutomation.Diagnostics.PoC")


class ExploitPoCExporter:
    """
    Automated exploit/payload replication engine.
    Captures precise session details and outputs ready-to-run Python exploit scripts.
    """

    @staticmethod
    def export_poc(
        url: str,
        method: str,
        headers: Dict[str, str],
        cookies: Dict[str, str],
        payload: Optional[str] = None,
        output_path: Optional[str] = None,
    ) -> str:
        target_file: Optional[str] = output_path
        if target_file is None:
            output_dir = pathlib.Path("./scratch")
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
                target_file = str(output_dir / "auto_exploit_poc.py")
            except (PermissionError, OSError) as pe:
                logger.warning(f"[PoC EXPORT] Could not create scratch directory: {pe}. Skipping disk write.")
                target_file = None
        else:
            try:
                pathlib.Path(target_file).parent.mkdir(parents=True, exist_ok=True)
            except (PermissionError, OSError) as pe:
                logger.warning(
                    f"[PoC EXPORT] Could not create parent directory for '{target_file}': {pe}. Skipping disk write."
                )
                target_file = None

        clean_headers = {k: v for k, v in headers.items() if not k.lower().startswith("sec-ch-ua")}
        poc_code = f"""# =====================================================================
# AUTOMATICALLY GENERATED EXPLOIT POC / REQUEST REPLICATOR
# Generated At: {time.strftime("%Y-%m-%d %H:%M:%S")}
# =====================================================================
import requests

url = "{url}"
method = "{method}"

headers = {repr(clean_headers)}
cookies = {repr(cookies)}
"""
        if payload:
            poc_code += f"\npayload = {repr(payload)}\n"
            poc_code += "response = requests.request(method, url, headers=headers, cookies=cookies, data=payload)\n"
        else:
            poc_code += "\nresponse = requests.request(method, url, headers=headers, cookies=cookies)\n"

        poc_code += """
print(f"[+] Exploit Execution Status Code: {response.status_code}")
print("[+] Response Headers:")
for k, v in response.headers.items():
    print(f"    {k}: {v}")
print("[+] Response Body Preview (First 500 chars):")
print(response.text[:500])
"""
        if target_file is not None:
            try:
                with open(target_file, "w", encoding="utf-8") as f:
                    f.write(poc_code)
                logger.info(f"[PoC EXPORT] Exploit PoC script generated successfully at: {target_file}")
            except (PermissionError, OSError) as pe:
                logger.warning(f"[PoC EXPORT] Could not write exploit PoC script to '{target_file}': {pe}")
        else:
            logger.info("[PoC EXPORT] Exploit PoC script generated in-memory (disk write skipped).")

        return poc_code
