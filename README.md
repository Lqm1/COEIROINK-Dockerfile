# COEIROINK-Dockerfile

COEIROINKをDocker上でホスティングするためのDockerfileとdocker-compose設定のコレクションです。このプロジェクトを使用することで、CPU環境とGPU環境の両方でCOEIROINK APIを簡単に実行できます。

## 概要

このリポジトリには以下のファイルが含まれています：

- `Dockerfile.cpu` - CPU環境向けのDockerfile
- `Dockerfile.gpu` - GPU環境向けのDockerfile
- `docker-compose-cpu.yml` - CPU環境向けのDocker Compose設定
- `docker-compose-gpu.yml` - GPU環境向けのDocker Compose設定
- `download.py` - COEIROINK実行ファイルの自動ダウンロードスクリプト

## 特徴

- 公式サイトから自動的にCOEIROINK実行ファイルをダウンロードして配置
- CPUとGPUの両方の環境に対応
- Nginxを使用したリバースプロキシにより、外部からのアクセスを可能に
- Dockerボリュームによるspeaker_infoの永続化で、話者の追加が容易
- ユーザープロファイルの既存のspeaker_infoディレクトリとの連携

## 使用方法

### CPU環境での実行

```bash
docker-compose -f docker-compose-cpu.yml up -d --build
```

### GPU環境での実行（NVIDIAドライバーとDocker GPU対応が必要）

```bash
docker-compose -f docker-compose-gpu.yml up -d --build
```

### アクセス方法

起動完了後、以下のURLでCOEIROINK APIにアクセスできます：

```
http://localhost:50032/
```

## ボリュームマウント

COEIROINK-Dockerfileは、以下のディレクトリをマウントして永続化します：

```
${USERPROFILE}/.local/share/COEIROINK-Engine/speaker_info:/app/coeiroink/speaker_info
```

これにより、Dockerコンテナを再作成しても話者情報が保持されます。また、ホストマシンのCOEIROINKアプリケーションと同じ話者情報を共有することも可能です。

## 注意事項

- このリポジトリにはCOEIROINKの実行ファイルは含まれていません。
- COEIROINKソフトウェアは一部であっても再配布が禁止されているため、イメージの配布は行われません。
- 必ずDockerfileを基に自身でイメージをビルドしてください。
- ビルド時にダウンロードスクリプトが自動的にCOEIROINK公式サイトから実行ファイルを入手します。

## 動作要件

- Docker
- Docker Compose
- GPU版を使用する場合：NVIDIA Container Toolkit

## ライセンス

このDockerfile及び関連ファイルのライセンスについては、LICENSEファイルを参照してください。
COEIROINKのライセンスについては、[公式サイト](https://coeiroink.com/)をご確認ください。