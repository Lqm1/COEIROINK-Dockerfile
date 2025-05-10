#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json5
import re
import sys
import zipfile
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


def parse_arguments() -> argparse.Namespace:
    """コマンドライン引数を解析します。"""
    parser = argparse.ArgumentParser(description="Coeiroink パッケージダウンローダー")
    parser.add_argument(
        "device",
        choices=["CPU", "GPU"],
        help="ダウンロードするデバイスタイプ (CPU または GPU)",
    )
    parser.add_argument(
        "--version",
        "-v",
        type=str,
        default=None,
        help="ダウンロードするバージョン (例: 2.9.0). 省略時は最新バージョンを自動選択",
    )
    return parser.parse_args()


def get_script_url(base_url: str, page_path: str) -> str:
    """ページからダウンロードスクリプトのURLを取得します。"""
    url = urljoin(base_url, page_path)
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    if script_tag := soup.select_one('script[src*="/download-"]'):
        return urljoin(base_url, str(script_tag["src"]))
    raise ValueError("ダウンロードスクリプトが見つかりませんでした")


def extract_json_data(script_url: str) -> dict:
    """スクリプトファイルからJSONデータを抽出します。"""
    response = requests.get(script_url)
    response.raise_for_status()

    if match := re.search(r"(?<=,e=)\{.*?\}(?=},\d+)", response.text, re.DOTALL):
        data = json5.loads(match.group(0))
        if not isinstance(data, dict):
            raise ValueError("抽出したデータが辞書形式ではありません")
        return data
    raise ValueError("スクリプト内からデータを抽出できませんでした")


def get_download_url(data: dict, version: str | None, device: str) -> str:
    """JSONデータから指定されたデバイス用のダウンロードURLを取得します。"""
    if not version:
        versions = sorted(data.keys(), key=lambda v: tuple(map(int, v.split("."))))
        version = versions[-1]

    try:
        return data[version]["Linux"][device]["DropBox"]
    except KeyError as e:
        raise ValueError(
            f"指定されたデバイス ({device}) のURLが見つかりませんでした: {e}"
        )


def download_and_extract(url: str, work_dir: Path) -> Path:
    """ファイルをダウンロードして解凍します。"""
    file_path = work_dir / Path(urlparse(url).path).name.split("?")[0]
    response = requests.get(url, stream=True)
    response.raise_for_status()

    with file_path.open("wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    extract_dir = work_dir / "coeiroink"
    with zipfile.ZipFile(file_path) as zipf:
        for member in zipf.namelist():
            if parts := Path(member).parts[1:]:
                dest = extract_dir.joinpath(*parts)
                dest.parent.mkdir(parents=True, exist_ok=True)
                if not member.endswith("/"):
                    dest.write_bytes(zipf.read(member))

    file_path.unlink()
    return extract_dir


def main() -> int:
    """メイン処理"""
    try:
        args = parse_arguments()
        work_dir = Path.cwd()
        script_url = get_script_url("https://coeiroink.com", "/download")

        json_data = extract_json_data(script_url)
        download_url = get_download_url(json_data, args.version, args.device)
        extract_dir = download_and_extract(download_url, work_dir)

        print(f"完了: Coeiroink は {extract_dir} に展開されました")
        return 0

    except requests.RequestException as e:
        print(f"ネットワークエラー: {e}")
    except (ValueError, KeyError) as e:
        print(f"データ処理エラー: {e}")
    except Exception as e:
        print(f"予期せぬエラー: {e}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
