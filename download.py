#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import json5
import re
import sys
import zipfile
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

BASE_URL = "https://coeiroink.com"
DOWNLOAD_PAGE_URL = f"{BASE_URL}/download"
NEXT_DATA_PATTERN = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">\s*(.*?)\s*</script>',
    re.DOTALL,
)
SCRIPT_SRC_PATTERN = re.compile(r'<script[^>]+src="([^"]+)"')
ROUTES_PATTERN = re.compile(r'e\.s\(\["ROUTES",0,(\{.*?\}),"ROUTES', re.DOTALL)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="COEIROINK の Linux 向けパッケージを Dropbox からダウンロードします。"
    )
    parser.add_argument(
        "--version",
        required=True,
        help="ダウンロードする COEIROINK バージョン (例: 2.12.3)",
    )
    device_group = parser.add_mutually_exclusive_group(required=True)
    device_group.add_argument(
        "--cpu",
        action="store_true",
        help="CPU 版をダウンロードします。",
    )
    device_group.add_argument(
        "--gpu",
        action="store_true",
        help="GPU 版をダウンロードします。",
    )
    return parser.parse_args()


def fetch_download_page(session: requests.Session) -> str:
    response = session.get(DOWNLOAD_PAGE_URL, timeout=30)
    response.raise_for_status()
    return response.text


def extract_latest_version(download_page_html: str) -> str:
    match = NEXT_DATA_PATTERN.search(download_page_html)
    if not match:
        raise ValueError("__NEXT_DATA__ が見つかりませんでした")

    next_data = json.loads(match.group(1))
    update_infos = next_data["props"]["pageProps"]["updateInfos"]
    if not update_infos:
        raise ValueError("アップデート情報が見つかりませんでした")

    return str(update_infos[0]["version"]).removeprefix("v.")


def extract_script_urls(download_page_html: str) -> list[str]:
    script_urls = []
    for script_src in SCRIPT_SRC_PATTERN.findall(download_page_html):
        absolute_url = urljoin(BASE_URL, script_src)
        if absolute_url not in script_urls:
            script_urls.append(absolute_url)
    if not script_urls:
        raise ValueError("ダウンロードページの script が見つかりませんでした")
    return script_urls


def extract_routes_from_script(script_text: str) -> dict:
    match = ROUTES_PATTERN.search(script_text)
    if not match:
        raise ValueError("ROUTES 定義が見つかりませんでした")

    routes = json5.loads(match.group(1))
    if not isinstance(routes, dict):
        raise ValueError("ROUTES の形式が不正です")
    return routes


def fetch_routes(session: requests.Session, script_urls: list[str]) -> dict:
    for script_url in script_urls:
        response = session.get(script_url, timeout=30)
        response.raise_for_status()
        try:
            return extract_routes_from_script(response.text)
        except ValueError:
            continue
    raise ValueError("ROUTES を含む script が見つかりませんでした")


def resolve_download_url(routes: dict, version: str, device: str) -> str:
    try:
        return routes[version]["Linux"][device]["DropBox"]
    except KeyError as exc:
        available_versions = ", ".join(sorted(routes.keys(), reverse=True))
        raise ValueError(
            f"Linux/{device}/DropBox の URL が見つかりませんでした。"
            f" version={version}, 利用可能バージョン={available_versions}"
        ) from exc


def download_file(session: requests.Session, url: str, destination: Path) -> None:
    with session.get(url, stream=True, timeout=300) as response:
        response.raise_for_status()
        with destination.open("wb") as file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    file.write(chunk)


def extract_archive(archive_path: Path, destination_dir: Path) -> Path:
    extract_dir = destination_dir / "coeiroink"
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            member_path = Path(member.filename)
            relative_parts = member_path.parts[1:] if len(member_path.parts) > 1 else ()
            if not relative_parts:
                continue

            output_path = extract_dir.joinpath(*relative_parts)
            if member.is_dir():
                output_path.mkdir(parents=True, exist_ok=True)
                continue

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, output_path.open("wb") as target:
                target.write(source.read())

    return extract_dir


def cleanup_previous_extract(destination_dir: Path) -> None:
    extract_dir = destination_dir / "coeiroink"
    if not extract_dir.exists():
        return

    for path in sorted(extract_dir.rglob("*"), reverse=True):
        if path.is_file() or path.is_symlink():
            path.unlink()
        elif path.is_dir():
            path.rmdir()
    extract_dir.rmdir()


def main() -> int:
    args = parse_arguments()
    device = "GPU" if args.gpu else "CPU"
    work_dir = Path.cwd()

    try:
        with requests.Session() as session:
            download_page_html = fetch_download_page(session)
            latest_version = extract_latest_version(download_page_html)
            script_urls = extract_script_urls(download_page_html)
            routes = fetch_routes(session, script_urls)
            download_url = resolve_download_url(routes, args.version, device)

            archive_name = Path(urlparse(download_url).path).name or (
                f"COEIROINK_LINUX_{device}_v.{args.version}.zip"
            )
            archive_path = work_dir / archive_name

            print(f"latest={latest_version}")
            print(f"version={args.version}")
            print(f"device={device}")
            print(f"url={download_url}")

            download_file(session, download_url, archive_path)
            cleanup_previous_extract(work_dir)
            extract_dir = extract_archive(archive_path, work_dir)
            archive_path.unlink()

        print(f"完了: {extract_dir} に展開しました")
        return 0

    except requests.RequestException as exc:
        print(f"ネットワークエラー: {exc}", file=sys.stderr)
    except (ValueError, KeyError, zipfile.BadZipFile) as exc:
        print(f"処理エラー: {exc}", file=sys.stderr)
    except Exception as exc:  # pragma: no cover
        print(f"予期しないエラー: {exc}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
