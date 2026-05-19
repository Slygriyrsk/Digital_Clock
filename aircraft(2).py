#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import random
import socket
import struct
import sys
import time
import uuid
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config as cfg
from telemetry import generate_telemetry, generate_audio
from compress  import compress_bundle, decompress_bundle, BUNDLE_HDR_SZ, BUNDLE_FMT
from crypto    import (ecdsa_keygen, ecdsa_sign, save_ecdsa_keys,
                        load_ecdsa_private, LatticeKey, benchmark)
from protocol  import (make_packet, parse_ack, FEC_K, FLAG_PARITY, FLAG_RETX)

os.makedirs("output", exist_ok=True)
os.makedirs("keys",   exist_ok=True)


class NetworkSim:
    def __init__(self):
        self._chunks_since_burst = 0
        self._burst_remaining    = 0
        self.stats = {"sent": 0, "burst_drops": 0}

    def should_drop(self, chunk_idx):
        if self._burst_remaining > 0:
            self._burst_remaining   -= 1
            self._chunks_since_burst = 0
            self.stats["burst_drops"] += 1
            print(f"  [BURST-DROP] chunk {chunk_idx}  "
                  f"({self._burst_remaining} more in this burst)")
            return True

        self._chunks_since_burst += 1
        if self._chunks_since_burst >= cfg.NET_BURST_EVERY_N:
            self._chunks_since_burst = 0
            self._burst_remaining    = cfg.NET_BURST_SIZE - 1
            self.stats["burst_drops"] += 1
            print(f"  [BURST-START] chunk {chunk_idx}  "
                  f"(burst of {cfg.NET_BURST_SIZE} — "
                  f"{self._burst_remaining} more to drop)")
            return True

        return False

    def record_sent(self):
        self.stats["sent"] += 1

    def print_summary(self):
        s     = self.stats
        total = s["sent"] + s["burst_drops"]
        pct   = 100 * s["burst_drops"] / max(1, total)
        print(f"\n  Network sim summary:")
        print(f"    Total attempted : {total}")
        print(f"    Sent OK         : {s['sent']}")
        print(f"    Burst drops     : {s['burst_drops']}  "
              f"(burst size={cfg.NET_BURST_SIZE}, "
              f"every {cfg.NET_BURST_EVERY_N} chunks)")
        print(f"    Loss rate       : {pct:.1f}%")


_net = NetworkSim()


def ensure_keys():
    if not os.path.exists(cfg.PRIVATE_KEY_PATH):
        priv, pub = ecdsa_keygen()
        save_ecdsa_keys(priv, pub)
        print(f"Keys generated -> {cfg.PRIVATE_KEY_PATH}")
        print(f"  Copy {cfg.PUBLIC_KEY_PATH} to ground station keys/ folder")
    return load_ecdsa_private()


def load_audio_file(path):
    if not os.path.exists(path):
        print(f"  [WARN] Audio file not found: {path}")
        print(f"  [WARN] Falling back to synthetic CVR audio.")
        return None, None

    ext = os.path.splitext(path)[1].lower()

    try:
        wf_handle = wave.open(path, "rb")
    except Exception as e:
        print(f"  [WARN] Cannot open {path} as WAV: {e}")
        print(f"  [WARN] Falling back to synthetic CVR audio.")
        return None, None

    with wf_handle as wf:
        src_rate  = wf.getframerate()
        channels  = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        n_frames  = wf.getnframes()
        raw       = wf.readframes(n_frames)

    print(f"  Audio in  : {path}")
    print(f"             {src_rate}Hz  {channels}ch  "
          f"{sampwidth*8}bit  {n_frames} frames  {len(raw):,}B")

    if sampwidth == 1:
        samples = [(b - 128) / 128.0 for b in raw]
    elif sampwidth == 2:
        n       = len(raw) // 2
        samples = [s / 32767.0 for s in struct.unpack(f"<{n}h", raw[:n*2])]
    elif sampwidth == 3:
        samples = []
        for i in range(0, len(raw) - 2, 3):
            v = raw[i] | (raw[i+1] << 8) | (raw[i+2] << 16)
            if v >= (1 << 23):
                v -= (1 << 24)
            samples.append(v / 8388607.0)
    elif sampwidth == 4:
        n       = len(raw) // 4
        samples = [s / 2147483647.0 for s in struct.unpack(f"<{n}i", raw[:n*4])]
    else:
        print(f"  [WARN] Unsupported bit depth {sampwidth*8}-bit. Falling back to synthetic.")
        return None, None

    if channels >= 2:
        samples = [samples[i] for i in range(0, len(samples) - (channels - 1), channels)]

    TARGET_RATE = 8000
    if src_rate != TARGET_RATE:
        ratio     = TARGET_RATE / src_rate
        new_n     = int(len(samples) * ratio)
        resampled = []
        for i in range(new_n):
            src_pos = i / ratio
            lo      = int(src_pos)
            hi      = min(lo + 1, len(samples) - 1)
            frac    = src_pos - lo
            resampled.append(samples[lo] * (1.0 - frac) + samples[hi] * frac)
        samples = resampled
        print(f"  Resampled : {src_rate}Hz -> {TARGET_RATE}Hz  "
              f"({n_frames} -> {len(samples)} samples)")

    pcm = struct.pack(f"<{len(samples)}h",
                      *[max(-32768, min(32767, int(s * 32767))) for s in samples])

    out_path = "output/cvr_input.wav"
    with wave.open(out_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(TARGET_RATE)
        wf.writeframes(pcm)

    print(f"  Audio out : {TARGET_RATE}Hz mono 16-bit  "
          f"{len(samples):,} samples  {len(pcm):,}B  -> {out_path}")
    return pcm, ext


def load_dtn_state():
    if os.path.exists(cfg.DTN_STATE_FILE):
        with open(cfg.DTN_STATE_FILE) as f:
            raw = json.load(f)
        raw["acked_chunks"] = set(raw.get("acked_chunks", []))
        raw["retry_count"]  = {int(k): v for k, v in raw.get("retry_count", {}).items()}
        raw["next_retry"]   = {int(k): v for k, v in raw.get("next_retry", {}).items()}
        return raw
    return {}


def save_dtn_state(state):
    out = {
        "session_id":   state["session_id"],
        "bundle_hash":  state["bundle_hash"],
        "total_chunks": state["total_chunks"],
        "acked_chunks": sorted(state["acked_chunks"]),
        "retry_count":  {str(k): v for k, v in state["retry_count"].items()},
        "next_retry":   {str(k): v for k, v in state["next_retry"].items()},
    }
    with open(cfg.DTN_STATE_FILE, "w") as f:
        json.dump(out, f)


def build_signed_bundle(session_id, private_key, audio_path=None):
    tele_raw, _ = generate_telemetry()

    resolved_path = audio_path or getattr(cfg, "CVR_AUDIO_PATH", None)
    audio_raw, audio_ext = None, None
    if resolved_path:
        audio_raw, audio_ext = load_audio_file(resolved_path)
    if audio_raw is None:
        print("  Audio     : generating synthetic CVR audio")
        audio_raw = generate_audio(mode="synthetic")
        audio_ext = ".wav"

    bundle          = compress_bundle(session_id, tele_raw, audio_raw, audio_ext)
    payload_to_sign = bundle[BUNDLE_HDR_SZ:]

    print("\n── Crypto comparison ─────────────────────────────────────")
    bm = benchmark(payload_to_sign, n=3)
    print(f"  ECDSA P-256  sign: {bm['ecdsa_sign_ms']:.1f}ms  "
          f"verify: {bm['ecdsa_verify_ms']:.1f}ms  sig: {bm['ecdsa_sig_bytes']}B")
    print(f"  Lattice-LWE  sign: {bm['lattice_sign_ms']:.1f}ms  "
          f"verify: {bm['lattice_verify_ms']:.1f}ms  sig: {bm['lattice_sig_bytes']}B  "
          f"ok: {bm['lattice_ok']}")
    print("──────────────────────────────────────────────────────────")

    ecdsa_sig   = ecdsa_sign(private_key, payload_to_sign)
    signed      = bundle + struct.pack("!H", len(ecdsa_sig)) + ecdsa_sig
    bundle_hash = hashlib.sha256(signed).hexdigest()

    print(f"\nSigned bundle: {len(signed):,}B  hash: {bundle_hash[:16]}...")
    return signed, bundle_hash


def split_signed(data):
    (_, _, t_id, a_id,
     tele_raw_len, tele_comp_len,
     audio_raw_len, audio_comp_len,
     audio_ext_b, sha) = struct.unpack_from(BUNDLE_FMT, data)
    bundle_end = BUNDLE_HDR_SZ + tele_comp_len + audio_comp_len
    if len(data) < bundle_end + 2:
        raise ValueError("Data truncated: cannot read signature length")
    sig_len = struct.unpack_from("!H", data, bundle_end)[0]
    bundle  = data[:bundle_end]
    sig     = data[bundle_end + 2: bundle_end + 2 + sig_len]
    return bundle, sig


def open_sockets():
    tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    rx.bind(("0.0.0.0", cfg.ACK_PORT))
    rx.settimeout(0.1)
    return tx, rx


def drain_acks(rx, acked):
    newly = set()
    while True:
        try:
            data, _ = rx.recvfrom(256)
            win_start, bitmap = parse_ack(data)
            for bit in range(64):
                if bitmap & (1 << bit):
                    acked.add(win_start + bit)
                    newly.add(win_start + bit)
        except (socket.timeout, ValueError):
            break
    return newly


def _xor_parity(payloads):
    max_len = max(len(p) for p in payloads)
    result  = bytearray(max_len)
    for p in payloads:
        for i, b in enumerate(p):
            result[i] ^= b
    return bytes(result)


def send_bundle(bundle, session_id, state):
    raw_chunks = [bundle[i:i+cfg.CHUNK_SIZE] for i in range(0, len(bundle), cfg.CHUNK_SIZE)]
    total      = len(raw_chunks)
    state["total_chunks"] = total

    fec_parities = {}
    for grp_start in range(0, total, FEC_K):
        grp_end = min(grp_start + FEC_K, total)
        grp_id  = grp_start // FEC_K
        fec_parities[grp_id] = _xor_parity(raw_chunks[grp_start:grp_end])

    tx, rx      = open_sockets()
    acked       = state["acked_chunks"]
    retry_count = state["retry_count"]
    next_retry  = state["next_retry"]
    seq         = state.get("last_seq", 0)

    elapsed_fmt = lambda: f"{time.time() - _net._session_t0:.1f}s"

    print(f"\n── Sending {total} chunks to {len(cfg.GROUND_STATIONS)} ground station(s) ──")
    print(f"   Stations     : {[gs['name'] for gs in cfg.GROUND_STATIONS]}")
    print(f"   Drop prob    : {cfg.NET_DROP_PROB*100:.0f}%  "
          f"burst={cfg.NET_BURST_SIZE}  "
          f"blackout=[{cfg.NET_BLACKOUT_START_S}s-{cfg.NET_BLACKOUT_END_S}s]")
    print(f"   ACKed already: {len(acked)}/{total}")

    def _send_chunk(idx, payload, flags=0, fec_grp=0):
        nonlocal seq
        seq += 1
        if not (flags & FLAG_PARITY) and _net.should_drop(idx):
            return seq
        pkt = make_packet(session_id, seq, idx, total, payload, flags, fec_grp)
        for gs in cfg.GROUND_STATIONS:
            try:
                tx.sendto(pkt, (gs["host"], gs["port"]))
            except OSError:
                pass
        _net.record_sent()
        return seq

    try:
        while len(acked) < total:
            now = time.time()
            drain_acks(rx, acked)

            for idx in range(total):
                if idx in acked:
                    continue
                if now < next_retry.get(idx, 0):
                    continue
                rc = retry_count.get(idx, 0)
                if rc > cfg.DTN_MAX_RETRIES:
                    print(f"  [GIVE UP] chunk {idx} after {rc} retries")
                    acked.add(idx)
                    continue

                grp_id   = idx // FEC_K
                flags    = FLAG_RETX if rc > 0 else 0
                last_seq = _send_chunk(idx, raw_chunks[idx], flags, grp_id)

                if (idx + 1) % FEC_K == 0 or idx == total - 1:
                    grp_start = grp_id * FEC_K
                    _send_chunk(grp_start, fec_parities[grp_id], FLAG_PARITY, grp_id)

                retry_count[idx] = rc + 1
                backoff           = min(cfg.DTN_BASE_SEC * (2 ** rc), cfg.DTN_MAX_SEC)
                next_retry[idx]   = now + backoff

                time.sleep(0.5)
                drain_acks(rx, acked)

                tag = "RETX" if rc > 0 else "SENT"
                print(f"  [{tag}] t={elapsed_fmt()}  chunk {idx+1:>4}/{total}  "
                      f"seq={last_seq:<5}  retry={rc}  "
                      f"acked={len(acked)}/{total}")

            state["last_seq"] = seq
            save_dtn_state(state)

            if len(acked) < total:
                still_missing  = [i for i in range(total) if i not in acked]
                earliest_retry = min(next_retry.get(i, 0) for i in still_missing)
                wait = max(0, earliest_retry - time.time())
                if wait > 0:
                    print(f"  [DTN] waiting {wait:.1f}s before next retry...")
                    time.sleep(min(wait, 2.0))

    except KeyboardInterrupt:
        print("\nInterrupted -- DTN state saved.")
    finally:
        _net.print_summary()
        tx.close()
        rx.close()


def main():
    ap = argparse.ArgumentParser(description="Aircraft sender")
    ap.add_argument("--audio", default=None,
                    help="Path to .wav recording (any sample rate, mono or stereo). "
                         "Falls back to config.CVR_AUDIO_PATH, then synthetic.")
    args = ap.parse_args()

    private_key = ensure_keys()
    session_id  = uuid.uuid4().bytes

    state = load_dtn_state()
    if state:
        print(f"Resuming DTN session {state['session_id'][:16]}... "
              f"({len(state['acked_chunks'])} chunks already ACKed)")
        session_id  = bytes.fromhex(state["session_id"])
        bundle_path = "output/bundle_signed.bin"
        if os.path.exists(bundle_path):
            with open(bundle_path, "rb") as f:
                bundle = f.read()
        else:
            bundle, bh = build_signed_bundle(session_id, private_key, args.audio)
            with open(bundle_path, "wb") as f:
                f.write(bundle)
    else:
        bundle, bundle_hash = build_signed_bundle(session_id, private_key, args.audio)
        bundle_path = "output/bundle_signed.bin"
        with open(bundle_path, "wb") as f:
            f.write(bundle)
        state = {
            "session_id":   session_id.hex(),
            "bundle_hash":  bundle_hash,
            "total_chunks": 0,
            "acked_chunks": set(),
            "retry_count":  {},
            "next_retry":   {},
        }
        save_dtn_state(state)
        print(f"New session: {session_id.hex()[:16]}...")

    print(f"\nGround stations : {[gs['name'] for gs in cfg.GROUND_STATIONS]}")
    print(f"ACK listen port : {cfg.ACK_PORT}")
    send_bundle(bundle, session_id, state)

    print(f"\nSession complete. Chunks ACKed: {len(state['acked_chunks'])}/{state['total_chunks']}")
    if len(state["acked_chunks"]) >= state["total_chunks"]:
        os.remove(cfg.DTN_STATE_FILE)
        print("DTN state cleared (all chunks ACKed).")


if __name__ == "__main__":
    main()
