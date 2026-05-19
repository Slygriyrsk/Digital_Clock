import os

GROUND_STATIONS = [
    {"host": "127.0.0.1", "port": 9000, "name": "GS-Primary"},
    {"host": "127.0.0.1", "port": 9001, "name": "GS-Backup"},
    {"host": "127.0.0.1", "port": 9002, "name": "GS-Charlie"},
]

ACK_PORT         = 9100
CHUNK_SIZE       = 900

PRIVATE_KEY_PATH = "keys/aircraft_private.pem"
PUBLIC_KEY_PATH  = "keys/aircraft_public.pem"
HMAC_KEY         = b"fdr-hmac-shared-2024"

DTN_BASE_SEC     = 1.0
DTN_MAX_SEC      = 30.0
DTN_MAX_RETRIES  = 10
DTN_STATE_FILE   = "output/dtn_state.json"

DURATION_SEC     = 60

FDR_COMPRESSION  = "lzma"
CVR_COMPRESSION  = "flac"

CVR_AUDIO_PATH   = None

NET_DROP_PROB        = 0.08
NET_BURST_SIZE       = 3
NET_BLACKOUT_START_S = 20
NET_BLACKOUT_END_S   = 35
NET_BASE_LATENCY_MS  = 40
NET_JITTER_MS        = 15
