#!/usr/bin/env python3
"""独立脚本：指定 box_id，拉该 box 下全部 RTSP，每 N 秒存 1 帧到 OSS。"""

import argparse
import os
import sys
import threading
import time
from datetime import datetime

import cv2
import oss2

OSS_AK = 'LTAI5tNqydfB79tGCQtEkqGs'
OSS_SK = 'P9KpxU63JBqiXcdfaEn4h7eA1hq4QYHO'
OSS_ENDPOINT = 'oss-ap-southeast-1.aliyuncs.com'
OSS_BUCKET = 'bo-usrdescription'
PLAYLIST = os.getenv("OSS_PLAYLIST_NAME", "data.m3u8")
OSS_DIR = os.getenv("OSS_DIR", "BO-USRDESCRIPTION-HEATMAP-DATA")


# ===================== 配置（只改这里） =====================
INTERVAL_SEC = 3          # 每隔几秒存 1 帧
MAX_WIDTH = 1920          # 上传前最大宽，0=不缩放
JPEG_QUALITY = 95
CONFIG_DIR = os.path.join(os.path.dirname(__file__), "config_box")
OSS_PREFIX = "raw-frames"  # OSS 根目录
# ===========================================================

# box_id -> store_id + camera_id -> rtsp_url
CAMERA_REGISTRY = {

    "1420125020341": {
        "store_id": "IDNV001",
        "cameras": {
            "DS-2CD3786G2-IZS20230731AAWRAE4588055": "rtsp://admin:bobo1212@192.168.10.212/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3786G2-IZS20230731AAWRAE4588060": "rtsp://admin:bobo1212@192.168.10.213/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421425079269": {
        "store_id": "IDOS078",
        "cameras": {
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749866": "rtsp://admin:bobo1212@192.168.10.190/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749837": "rtsp://admin:bobo1212@192.168.10.191/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749832": "rtsp://admin:bobo1212@192.168.10.192/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749831": "rtsp://admin:bobo1212@192.168.10.193/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749834": "rtsp://admin:bobo1212@192.168.10.194/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421425079277": {
        "store_id": "IDNV056",
        "cameras": {
            "DS-2CD3786G2-IZS20230731AAWRAE4588061": "rtsp://admin:bobo1212@192.168.10.165/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3786G2-IZS20230731AAWRAE4588059": "rtsp://admin:bobo1212@192.168.10.163/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3786G2-IZS20230731AAWRAE4588053": "rtsp://admin:bobo1212@192.168.10.162/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3786G2-IZS20230731AAWRAE4588056": "rtsp://admin:bobo1212@192.168.10.164/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625036572": {
        "store_id": "IDOS061",
        "cameras": {
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749877": "rtsp://admin:bobo1212@192.168.10.230/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625036622": {
        "store_id": "IDNV048",
        "cameras": {
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749853": "rtsp://admin:bobo1212@192.168.10.249/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749865": "rtsp://admin:bobo1212@192.168.10.248/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625036637": {
        "store_id": "IDNV068",
        "cameras": {
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069514": "rtsp://admin:bobo1212@192.168.10.203/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069461": "rtsp://admin:bobo1212@192.168.10.204/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625036649": {
        "store_id": "IDNV039",
        "cameras": {
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069500": "rtsp://admin:bobo1212@192.168.10.190/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069464": "rtsp://admin:bobo1212@192.168.10.191/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069449": "rtsp://admin:bobo1212@192.168.10.192/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069457": "rtsp://admin:bobo1212@192.168.10.193/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625036654": {
        "store_id": "IDNV016",
        "cameras": {
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749856": "rtsp://admin:bobo1212@192.168.10.186/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625036655": {
        "store_id": "IDNV017",
        "cameras": {
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749869": "rtsp://admin:bobo1212@192.168.10.196/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625036657": {
        "store_id": "IDNV033",
        "cameras": {
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749858": "rtsp://admin:bobo1212@192.168.10.180/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749852": "rtsp://admin:bobo1212@192.168.10.181/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749840": "rtsp://admin:bobo1212@192.168.10.182/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749863": "rtsp://admin:bobo1212@192.168.10.184/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625036663": {
        "store_id": "IDNV014",
        "cameras": {
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069463": "rtsp://admin:bobo1212@192.168.10.188/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069482": "rtsp://admin:bobo1212@192.168.10.189/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069477": "rtsp://admin:bobo1212@192.168.10.190/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625036682": {
        "store_id": "IDOS071",
        "cameras": {
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749829": "rtsp://admin:bobo1212@192.168.10.192/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749841": "rtsp://admin:bobo1212@192.168.10.193/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625036722": {
        "store_id": "IDNV028",
        "cameras": {
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749848": "rtsp://admin:bobo1212@192.168.10.182/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749875": "rtsp://admin:bobo1212@192.168.10.186/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749844": "rtsp://admin:bobo1212@192.168.10.187/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749849": "rtsp://admin:bobo1212@192.168.10.185/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625036749": {
        "store_id": "IDOS095",
        "cameras": {
            "DS-2CD3786G2-IZS20240805AAWRFK5689313": "rtsp://admin:bobo1212@192.168.10.190/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3786G2-IZS20240805AAWRFK5689289": "rtsp://admin:bobo1212@192.168.10.191/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3786G2-IZS20240805AAWRFK5689214": "rtsp://admin:bobo1212@192.168.10.192/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625036754": {
        "store_id": "IDNV018",
        "cameras": {
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069448": "rtsp://admin:bobo1212@192.168.10.187/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069495": "rtsp://admin:bobo1212@192.168.10.188/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625036761": {
        "store_id": "IDOS089",
        "cameras": {
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749874": "rtsp://admin:bobo1212@192.168.10.195/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749873": "rtsp://admin:bobo1212@192.168.10.196/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625036774": {
        "store_id": "IDNV022",
        "cameras": {
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069516": "rtsp://admin:bobo1212@192.168.10.235/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069508": "rtsp://admin:bobo1212@192.168.10.236/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069502": "rtsp://admin:bobo1212@192.168.10.237/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625036793": {
        "store_id": "IDNV053",
        "cameras": {
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069481": "rtsp://admin:bobo1212@192.168.10.204/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625036795": {
        "store_id": "IDNV066",
        "cameras": {
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069491": "rtsp://admin:bobo1212@192.168.10.203/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069507": "rtsp://admin:bobo1212@192.168.10.204/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625036799": {
        "store_id": "IDNV041",
        "cameras": {
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749859": "rtsp://admin:bobo1212@192.168.10.179/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749850": "rtsp://admin:bobo1212@192.168.10.180/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749854": "rtsp://admin:bobo1212@192.168.10.181/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625036801": {
        "store_id": "IDNV002",
        "cameras": {
            "DS-2CD3786G2-IZS20230731AAWRAE4588058": "rtsp://admin:bobo1212@192.168.10.185/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3786G2-IZS20230731AAWRAE4588054": "rtsp://admin:bobo1212@192.168.10.188/ISAPI/Streaming/Channels/101?tcp",
            "210235TD3XF19A000599": "rtsp://admin:admin123@192.168.10.148/cam/realmonitor?channel=1&subtype=0",
            "210235TD3XF19A000607": "rtsp://admin:admin123@192.168.10.151/cam/realmonitor?channel=1&subtype=0",
            "210235TD3XF19A000624": "rtsp://admin:admin123@192.168.10.156/cam/realmonitor?channel=1&subtype=0",
            "210235TD3XF19A000696": "rtsp://admin:admin123@192.168.10.167/cam/realmonitor?channel=1&subtype=0",
            "210235TD3XF19A000625": "rtsp://admin:admin123@192.168.10.171/cam/realmonitor?channel=1&subtype=0",
            "210235TD3XF19A000598": "rtsp://admin:admin123@192.168.10.178/cam/realmonitor?channel=1&subtype=0",
        },
    },
    "1421625036805": {
        "store_id": "IDNV043",
        "cameras": {
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069486": "rtsp://admin:bobo1212@192.168.10.187/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069466": "rtsp://admin:bobo1212@192.168.10.188/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625036826": {
        "store_id": "IDNV054",
        "cameras": {
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069451": "rtsp://admin:bobo1212@192.168.10.194/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625036829": {
        "store_id": "IDNV067",
        "cameras": {
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069445": "rtsp://admin:bobo1212@192.168.10.190/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069460": "rtsp://admin:bobo1212@192.168.10.191/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069485": "rtsp://admin:bobo1212@192.168.10.192/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625036929": {
        "store_id": "IDNV032",
        "cameras": {
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069473": "rtsp://admin:bobo1212@192.168.10.183/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069465": "rtsp://admin:bobo1212@192.168.10.184/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625036933": {
        "store_id": "IDNV029",
        "cameras": {
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749860": "rtsp://admin:bobo1212@192.168.10.183/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749867": "rtsp://admin:bobo1212@192.168.10.184/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749839": "rtsp://admin:bobo1212@192.168.10.185/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625036972": {
        "store_id": "IDNV008",
        "cameras": {
            "20250911AAWRGF6108229": "rtsp://admin:bobo1212@192.168.10.197/ISAPI/Streaming/Channels/101?tcp",
            "20250911AAWRGF6108253": "rtsp://admin:bobo1212@192.168.10.198/ISAPI/Streaming/Channels/101?tcp",
            "20250911AAWRGF6108224": "rtsp://admin:bobo1212@192.168.10.199/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069494": "rtsp://admin:bobo1212@192.168.10.200/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625037007": {
        "store_id": "IDNV012",
        "cameras": {
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069505": "rtsp://admin:bobo1212@192.168.10.175/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069444": "rtsp://admin:bobo1212@192.168.10.176/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625037093": {
        "store_id": "IDNV013",
        "cameras": {
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749842": "rtsp://admin:bobo1212@192.168.10.180/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749871": "rtsp://admin:bobo1212@192.168.10.182/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625037152": {
        "store_id": "IDOS098",
        "cameras": {
            "DS-2CD3786G2-IZS20240805AAWRFK5689197": "rtsp://admin:bobo1212@192.168.10.216/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069509": "rtsp://admin:bobo1212@192.168.10.217/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069456": "rtsp://admin:bobo1212@192.168.10.218/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069452": "rtsp://admin:bobo1212@192.168.10.219/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625037155": {
        "store_id": "IDOS090",
        "cameras": {
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749870": "rtsp://admin:bobo1212@192.168.10.178/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749861": "rtsp://admin:bobo1212@192.168.10.179/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749843": "rtsp://admin:bobo1212@192.168.10.180/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625037171": {
        "store_id": "IDNV060",
        "cameras": {
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069503": "rtsp://admin:bobo1212@192.168.10.202/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069512": "rtsp://admin:bobo1212@192.168.10.203/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069493": "rtsp://admin:bobo1212@192.168.10.204/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625037243": {
        "store_id": "IDNV058",
        "cameras": {
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069453": "rtsp://admin:bobo1212@192.168.10.195/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069469": "rtsp://admin:bobo1212@192.168.10.196/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069467": "rtsp://admin:bobo1212@192.168.10.197/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069501": "rtsp://admin:bobo1212@192.168.10.198/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625037247": {
        "store_id": "IDNV055",
        "cameras": {
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749872": "rtsp://admin:bobo1212@192.168.10.198/ISAPI/Streaming/Channels/101?tcp",
            "D6P-B20230706AACHAD4829798": "rtsp://admin:admin123@192.168.10.143/cam/realmonitor?channel=1&subtype=0",
            "D6P-B20230706AACHAD4829789": "rtsp://admin:admin123@192.168.10.146/cam/realmonitor?channel=1&subtype=0",
        },
    },
    "1421625037248": {
        "store_id": "IDNV025",
        "cameras": {
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069483": "rtsp://admin:bobo1212@192.168.10.173/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069518": "rtsp://admin:bobo1212@192.168.10.174/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625037249": {
        "store_id": "IDNV042",
        "cameras": {
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749855": "rtsp://admin:bobo1212@192.168.10.192/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749833": "rtsp://admin:bobo1212@192.168.10.193/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625037278": {
        "store_id": "IDOS077",
        "cameras": {
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749828": "rtsp://admin:bobo1212@192.168.10.211/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749851": "rtsp://admin:bobo1212@192.168.10.212/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625037286": {
        "store_id": "IDNV049",
        "cameras": {
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749876": "rtsp://admin:bobo1212@192.168.10.202/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749835": "rtsp://admin:bobo1212@192.168.10.203/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749830": "rtsp://admin:bobo1212@192.168.10.204/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625037291": {
        "store_id": "IDNV031",
        "cameras": {
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069468": "rtsp://admin:bobo1212@192.168.10.192/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069462": "rtsp://admin:bobo1212@192.168.10.193/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069497": "rtsp://admin:bobo1212@192.168.10.194/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625037321": {
        "store_id": "IDNV064",
        "cameras": {
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069515": "rtsp://admin:bobo1212@192.168.10.236/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069492": "rtsp://admin:bobo1212@192.168.10.237/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069498": "rtsp://admin:bobo1212@192.168.10.238/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625037327": {
        "store_id": "IDNV045",
        "cameras": {
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069454": "rtsp://admin:bobo1212@192.168.1.249/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069499": "rtsp://admin:bobo1212@192.168.1.250/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069470": "rtsp://admin:bobo1212@192.168.1.251/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625037341": {
        "store_id": "IDNV019",
        "cameras": {
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069496": "rtsp://admin:bobo1212@192.168.10.181/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069471": "rtsp://admin:bobo1212@192.168.10.182/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069459": "rtsp://admin:bobo1212@192.168.10.183/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625037347": {
        "store_id": "IDOS090_map",
        "cameras": {
            "D10P20210526AACHG08053974": "rtsp://admin:admin123@192.168.10.144/cam/realmonitor?channel=1&subtype=0",
            "D10P20210526AACHG08054025": "rtsp://admin:admin123@192.168.10.145/cam/realmonitor?channel=1&subtype=0",
            "DS-2CD3121G2E-LIU20240910AAWRFN4334716": "rtsp://admin:wdz147258@192.168.10.146/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3121G2E-LIU20240910AAWRFN4334708": "rtsp://admin:wdz147258@192.168.10.147/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3121G2E-LIU20240910AAWRFN4334897": "rtsp://admin:wdz147258@192.168.10.150/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3121G2E-LIU20240910AAWRFN4334724": "rtsp://admin:wdz147258@192.168.10.151/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3121G2E-LIU20240910AAWRFN4334720": "rtsp://admin:wdz147258@192.168.10.153/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3121G2E-LIU20240910AAWRFN4334719": "rtsp://admin:wdz147258@192.168.10.155/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3121G2E-LIU20240910AAWRFN4334913": "rtsp://admin:wdz147258@192.168.10.160/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3121G2E-LIU20240910AAWRFN4334714": "rtsp://admin:wdz147258@192.168.10.162/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3121G2E-LIU20240910AAWRFN4334896": "rtsp://admin:wdz147258@192.168.10.164/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3121G2E-LIU20240910AAWRFN4334717": "rtsp://admin:wdz147258@192.168.10.168/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3121G2E-LIU20240910AAWRFN4334718": "rtsp://admin:wdz147258@192.168.10.170/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625037401": {
        "store_id": "IDNV011",
        "cameras": {
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069480": "rtsp://admin:bobo1212@192.168.10.170/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069506": "rtsp://admin:bobo1212@192.168.10.171/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625037485": {
        "store_id": "IDNV007",
        "cameras": {
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749836": "rtsp://admin:bobo1212@192.168.10.180/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749864": "rtsp://admin:bobo1212@192.168.10.181/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749847": "rtsp://admin:bobo1212@192.168.10.182/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625037489": {
        "store_id": "IDNV044",
        "cameras": {
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749846": "rtsp://admin:bobo1212@192.168.10.191/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749838": "rtsp://admin:bobo1212@192.168.10.192/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250703AAWRGC4749845": "rtsp://admin:bobo1212@192.168.10.193/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1421625037490": {
        "store_id": "IDNV035",
        "cameras": {
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069476": "rtsp://admin:bobo1212@192.168.10.197/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3781G2-LIZSU20250904AAWRGF3069472": "rtsp://admin:bobo1212@192.168.10.198/ISAPI/Streaming/Channels/101?tcp",
        },
    },
    "1423724335660": {
        "store_id": "IDNV021",
        "cameras": {
            "DS-2CD3786G2-IZS20240805AAWRFK5689303": "rtsp://admin:bobo1212@192.168.10.184/ISAPI/Streaming/Channels/101?tcp",
            "DS-2CD3786G2-IZS20230731AAWRAE4588057": "rtsp://admin:bobo1212@192.168.10.185/ISAPI/Streaming/Channels/101?tcp",
        },
    },
}


def resolve_camera(box_id: str, camera_id: str) -> tuple[str, str, str]:
    if box_id not in CAMERA_REGISTRY:
        raise KeyError(f"未知 box_id: {box_id}")
    box = CAMERA_REGISTRY[box_id]
    cameras = box["cameras"]
    if camera_id in cameras:
        cam_key = camera_id
    else:
        matches = [k for k in cameras if k.endswith(camera_id) or camera_id in k]
        if len(matches) == 1:
            cam_key = matches[0]
        else:
            raise KeyError(f"camera_id 未找到: {camera_id}，可用: {list(cameras.keys())}")
    return cameras[cam_key], box["store_id"], cam_key


def open_rtsp(url: str) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
    if not cap.isOpened():
        raise RuntimeError(f"无法打开 RTSP: {url}")
    return cap


def _log(cam_key: str, msg: str) -> None:
    print(f"[{cam_key[-15:]}] {msg}", flush=True)


def run_one(
    box_id: str,
    camera_id: str,
    duration: int | None,
    bucket: oss2.Bucket,
) -> int:
    rtsp_url, store_id, cam_key = resolve_camera(box_id, camera_id)
    cap = open_rtsp(rtsp_url)
    prefix = f"{OSS_PREFIX}/{store_id}/{cam_key[-15:]}/{datetime.now():%Y%m%d_%H%M%S}"
    _log(cam_key, f"RTSP: {rtsp_url}")
    _log(cam_key, f"OSS : oss://{OSS_BUCKET}/{prefix}/")

    next_save = time.time()
    idx = 0
    deadline = time.time() + duration if duration else None
    try:
        while deadline is None or time.time() < deadline:
            ret, frame = cap.read()
            if not ret:
                _log(cam_key, "读帧失败，退出")
                break
            if time.time() < next_save:
                continue
            next_save = time.time() + INTERVAL_SEC
            if MAX_WIDTH and frame.shape[1] > MAX_WIDTH:
                s = MAX_WIDTH / frame.shape[1]
                frame = cv2.resize(frame, (MAX_WIDTH, int(frame.shape[0] * s)))
            ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
            if ok:
                bucket.put_object(f"{prefix}/frame_{idx:06d}.jpg", buf.tobytes())
                idx += 1
                if idx % 10 == 0:
                    _log(cam_key, f"已上传 {idx} 帧")
    finally:
        cap.release()
    _log(cam_key, f"完成，共 {idx} 帧")
    return idx


def parse_camera_ids(camera_args: list[str]) -> list[str]:
    ids: list[str] = []
    for item in camera_args:
        ids.extend(part.strip() for part in item.split(",") if part.strip())
    if not ids:
        raise ValueError("未指定 camera_id")
    return ids


def run_multi(box_id: str, camera_ids: list[str], duration: int | None = None) -> int:
    bucket = oss2.Bucket(oss2.Auth(OSS_AK, OSS_SK), OSS_ENDPOINT, OSS_BUCKET)
    results: dict[str, int] = {}
    lock = threading.Lock()

    def worker(camera_id: str) -> None:
        try:
            count = run_one(box_id, camera_id, duration, bucket)
        except Exception as exc:
            _log(camera_id, f"错误: {exc}")
            count = 0
        with lock:
            results[camera_id] = count

    threads = [
        threading.Thread(target=worker, args=(camera_id,), name=camera_id[-15:])
        for camera_id in camera_ids
    ]
    print(f"启动 {len(threads)} 路摄像头，box_id={box_id}", flush=True)
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    total = sum(results.values())
    print(f"全部完成，{len(camera_ids)} 路，合计 {total} 帧", flush=True)
    for camera_id, count in results.items():
        print(f"  {camera_id}: {count} 帧", flush=True)
    return total


def list_cameras() -> None:
    for box_id, info in sorted(CAMERA_REGISTRY.items()):
        print(f"[{box_id}] store={info['store_id']}")
        for cid in info["cameras"]:
            print(f"  {cid}")


def cameras_for_box(box_id: str) -> list[str]:
    if box_id not in CAMERA_REGISTRY:
        raise KeyError(f"未知 box_id: {box_id}")
    return list(CAMERA_REGISTRY[box_id]["cameras"].keys())


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--box_id", default="1420125020341")
    p.add_argument(
        "--camera_id",
        action="append",
        help="可选，指定部分摄像头；不指定则跑该 box 下全部摄像头",
    )
    p.add_argument("--duration", type=int, default=60)
    p.add_argument("--list", action="store_true", help="列出内置 box/camera")
    args = p.parse_args()
    if args.list:
        list_cameras()
        sys.exit(0)
    try:
        if args.camera_id:
            camera_ids = parse_camera_ids(args.camera_id)
        else:
            camera_ids = cameras_for_box(args.box_id)
        run_multi(args.box_id, camera_ids, args.duration)
    except KeyboardInterrupt:
        sys.exit(0)
    except KeyError as exc:
        sys.exit(str(exc))

