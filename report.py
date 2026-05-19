#!/usr/bin/env python3
import glob
import json
import os
import struct
import sys
import time
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


PARAM_DEFS = [
    ("Time",                            4, "sin",    0,     45000),
    ("Relative Time Count",             4, "sin",  100,       550),
    ("GPS Time Sync",                   4, "sin",    0,     45000),
    ("Pressure Altitude",               4, "sin",  100,       550),
    ("Indicated Airspeed",              8, "osc",  -20,        20),
    ("Heading",                         8, "osc",  -45,        45),
    ("Normal Acceleration",             4, "sin",    0,       360),
    ("Pitch Attitude",                  8, "osc",   -5,        20),
    ("Roll Attitude",                   4, "noise", -5,         5),
    ("Radio Transmission Keying",       4, "sin",    0,      2500),
    ("Engine Thrust Power",             4, "ramp",   0,       360),
    ("Cockpit Thrust Lever Position",   1, "ramp",   0,       360),
    ("Engine Thrust Parameter 2",       4, "sin",    0,       550),
    ("Flaps",                           2, "ramp",   0,       360),
    ("Trailing Edge Flap Position",     2, "ramp",  -90,       90),
    ("Cockpit Control Selection",       2, "sin",    0,     45000),
    ("Slats",                           1, "sin",    0,      0.95),
    ("Leading Edge Flap Position",      4, "sin",   -5,        20),
    ("Cockpit Control Slats",           4, "sin",   -5,        20),
    ("Thrust Reverse Status",           4, "sin",    0,      2500),
    ("Ground Spoiler Speed Brake",      4, "osc",   -1,         4),
    ("Ground Spoiler Position",         4, "osc",   -5,         5),
    ("Ground Spoiler Selection",        8, "noise", -10,       10),
    ("Speed Brake Position",            8, "noise", -10,       10),
    ("Speed Brake Selection",           4, "sin",    0,       360),
    ("Total Air Temperature OAT",       4, "ramp",   0,       360),
    ("Autopilot Autothrottle Mode",     2, "ramp",   0,       360),
    ("Longitudinal Acceleration",       2, "ramp",  -90,       90),
    ("Lateral Acceleration",            2, "sin",    0,     45000),
    ("Primary Flight Control Surface",  1, "sin",    0,      0.95),
    ("Pitch Axis Control",              4, "sin",   -5,        20),
    ("Roll Axis Control",               4, "sin",   -5,        20),
    ("Yaw Axis Control",                4, "sin",    0,      2500),
    ("Pitch Trim Surface Position",     4, "sin",    0,       360),
    ("Radio Altitude",                  1, "ramp",   0,       360),
    ("Vertical Beam Deviation",         1, "binary", 0,       360),
    ("ILS GPS Glide Path",              1, "binary", 0,       360),
    ("MLS Elevation",                   1, "steady", 0,         7),
    ("IRNAV Vertical Deviation",        1, "binary", 0,         1),
    ("Horizontal Beam Deviation",       1, "binary", 0,         1),
    ("ILS GPS Localizer",               1, "binary", 0,         1),
    ("MLS Azimuth",                     1, "binary", 0,         1),
    ("IRNAV Lateral Deviation",         1, "binary", 0,         1),
    ("Marker Beacon Passage",           1, "binary", 0,         1),
    ("Warnings and Cautions",           1, "steady", 0,      8000),
    ("Warnings",                        1, "steady", 0,         9),
    ("Cautions",                        1, "steady", 18,       26),
    ("Nav Receiver Frequency",          1, "steady", 100,     500),
    ("DME Distances",                   1, "steady", 20,       50),
    ("Distance to Runway Threshold",    1, "steady", 20,       50),
    ("Distance to Missed Approach",     1, "steady", 20,       50),
    ("Air Ground Status",               2, "noise",   0,        5),
    ("GPWS TAWS Status",                2, "noise",   0,        5),
    ("Terrain Display Mode",            4, "sin",    0,      2500),
    ("Terrain Alerts",                  4, "sin",    0,       360),
    ("On Off Switch Position",          4, "sin",  100,       550),
    ("Angle of Attack",                 4, "osc",  -20,        20),
    ("Hydraulic Pressure Low Warning",  8, "osc",  -45,        45),
    ("Hydraulic Pressure",              4, "sin",    0,       360),
    ("Pneumatic Pressure",              8, "osc",   -5,        20),
    ("Groundspeed",                     4, "noise", -5,         5),
    ("Landing Gear",                    4, "noise", -10,       10),
    ("Landing Gear Position",           4, "osc",   -1,         4),
    ("Gear Selector Position",          4, "ramp",   0,       360),
    ("Navigation Data",                 4, "ramp",  -90,       90),
    ("Drift Angle",                     2, "ramp",   0,       360),
    ("Wind Speed",                      2, "ramp", -180,      180),
    ("Wind Direction",                  2, "sin",    0,      2500),
    ("Latitude Longitude",              4, "sin",    0,       360),
    ("GPS Correction In Use",           4, "sin",  100,       550),
    ("Estimated Position Error",        4, "osc",  -20,        20),
    ("GNSS Altitude",                   4, "osc",  -45,        45),
    ("Brakes",                          8, "noise",  0,       360),
    ("Left Right Brake Pressure",       8, "noise", -5,         5),
    ("Left Right Brake Pedal Position", 4, "sin",    0,       360),
    ("Brake Temperature",               4, "ramp",   0,       360),
    ("Autobrake Level Selection",       1, "ramp",   0,       360),
    ("Anti Skid System Activation",     1, "sin",    0,     45000),
    ("Additional Engine Parameters",    1, "sin",    0,      0.95),
    ("EPR",                             4, "sin",   -5,        20),
    ("N1",                              4, "sin",   -5,        20),
    ("Indicated Vibration Level",       4, "sin",    0,      2500),
    ("N2",                              4, "sin",  100,       550),
    ("EGT",                             4, "osc",  -20,        20),
    ("Fuel Flow",                       4, "osc",  -45,        45),
    ("Fuel Cut Off Lever Position",     4, "osc",    0,       360),
    ("N3",                              4, "noise", -5,         5),
    ("Engine Fuel Metering Valve",      4, "noise", -10,       10),
    ("Engine Oil Pressure",             4, "noise", -10,       10),
    ("Blade Angle Turboprop",           4, "osc",   -1,         4),
    ("Condition Lever Position",        8, "noise", -5,         5),
    ("TCAS ACAS",                       8, "noise", -10,       10),
    ("Windshear Warning Caution",       4, "osc",   -1,         4),
    ("Selected Barometric Setting",     4, "osc",   -5,         5),
    ("Pilot Barometric Setting",        4, "noise", -10,       10),
    ("First Officer Barometric",        4, "noise", -3,         3),
    ("Selected Altitude",               4, "osc", -2000,     2000),
    ("Selected Speed",                  4, "ramp",   0,       360),
    ("Selected Mach",                   1, "ramp",   0,       360),
    ("Selected Vertical Speed",         1, "sin",    0,      0.95),
    ("Selected Heading",                1, "sin",   -5,        20),
    ("Selected Flight Path",            1, "steady", -5,       20),
    ("Course DSTRK",                    1, "steady",  0,     2500),
    ("Path Angle",                      1, "steady",  0,      360),
    ("Final Approach Path",             1, "steady",  0,      360),
    ("Selected Decision Height",        1, "ramp",    0,      360),
    ("EFIS Display Format",             1, "step",    0,      360),
    ("Pilot EFIS Display Format",       1, "step",    0,      360),
    ("First Officer EFIS Format",       1, "binary",  0,      360),
    ("Multi Engine Alerts Display",     1, "binary",  0,      360),
    ("AC Electrical Bus Status",        1, "binary",  0,        7),
    ("DC Electrical Bus Status",        1, "binary",  0,        7),
    ("Engine Bleed Valve Position",     1, "binary",  0,        1),
    ("APU Bleed Valve Position",        1, "binary",  0,        1),
    ("Computer Failure",                1, "binary",  0,        1),
    ("Engine Thrust Command",           1, "steady",  0,     8000),
    ("Engine Thrust Target",            1, "steady",  0,        9),
    ("Computed Centre of Gravity",      1, "steady", 18,       26),
    ("Fuel Quantity Tank System",       1, "steady", 100,     500),
    ("Head Up Display In Use",          1, "steady", 20,       50),
    ("Para Visual Display On",          1, "steady", 20,       50),
    ("Stall Protection Activation",     1, "binary",  0,        1),
    ("Primary Navigation System",       1, "binary",  0,        1),
    ("Ice Detection",                   1, "binary",  0,        1),
    ("Engine Warning Vibration",        1, "binary",  0,        1),
    ("Engine Warning Over Temperature", 1, "binary",  0,        1),
    ("Engine Warning Oil Pressure Low", 1, "binary",  0,        1),
    ("Engine Warning Over Speed",       1, "binary",  0,        1),
    ("Yaw Trim Surface Position",       1, "binary",  0,        1),
    ("Roll Trim Surface Position",      1, "binary",  0,        1),
    ("Yaw Or Sideslip Angle",           1, "binary",  0,        1),
    ("De Icing Anti Icing Selection",   1, "binary",  0,        1),
    ("Hydraulic Pressure Each System",  1, "binary",  0,        1),
    ("Loss Of Cabin Pressure",          1, "binary",  0,        1),
    ("Cockpit Trim Pitch",              1, "binary",  0,        1),
    ("Cockpit Trim Roll",               1, "binary",  0,        1),
    ("Cockpit Trim Yaw",                1, "binary",  0,        1),
    ("All Cockpit Flight Control Forces",1,"binary",  0,        1),
    ("Control Wheel Forces",            1, "binary",  0,        1),
    ("Control Column Forces",           1, "binary",  0,        1),
    ("Rudder Pedal Forces",             1, "binary",  0,        1),
    ("Event Marker",                    1, "ramp",    0,     3600),
    ("Date",                            1, "steady",  0,     1024),
    ("ANP EPE EPU",                     1, "binary",  0,        1),
    ("Cabin Pressure Altitude",         1, "binary",  0,        1),
    ("Aircraft Computed Weight",        1, "binary",  0,        1),
    ("Flight Director Command",         1, "binary",  0,        1),
    ("Left Flight Director Pitch",      1, "binary",  0,        1),
    ("Left Flight Director Roll",       1, "binary",  0,        1),
    ("Right Flight Director Pitch",     1, "binary",  0,        1),
    ("Right Flight Director Roll",      1, "binary",  0,        1),
    ("Vertical Speed",                  1, "binary",  0,        1),
    ("Cabin Pressure Control",          1, "binary",  0,        1),
    ("Cabin Altitude Rate",             1, "binary",  0,        1),
    ("Outflow Valve Position",          1, "binary",  0,        1),
    ("Cabin Pressurisation Mode",       1, "binary",  0,        1),
    ("Nose Wheel Steering",             1, "binary",  0,        1),
    ("Nose Wheel Steering Angle",       1, "binary",  0,        1),
    ("Nose Wheel Steering Control",     1, "binary",  0,        1),
    ("Aircraft Track",                  1, "binary",  0,        1),
    ("True Airspeed Mach Number",       1, "binary",  0,        1),
    ("True Airspeed",                   1, "binary",  0,        1),
    ("Mach Number",                     1, "binary",  0,        1),
    ("Takeoff Performance Parameters",  1, "binary",  0,        1),
    ("Vr Rotation Speed",               1, "binary",  0,        1),
    ("V1",                              1, "binary",  0,        1),
    ("V2",                              1, "binary",  0,        1),
    ("Selected Takeoff Modes",          1, "binary",  0,        1),
    ("Designation Active Procedures",   1, "binary",  0,        1),
    ("Selected SID Route",              1, "binary",  0,        1),
    ("Selected STAR Route",             1, "binary",  0,        1),
    ("Next Active Waypoint",            1, "binary",  0,        1),
    ("Runway Selected For Landing",     1, "binary",  0,        1),
    ("Attitude Rates",                  1, "binary",  0,        1),
    ("Pitch Rate",                      1, "binary",  0,        1),
    ("Roll Rate",                       1, "binary",  0,        1),
    ("Yaw Rate",                        1, "binary",  0,        1),
    ("Wheel Speed",                     1, "binary",  0,        1),
    ("Crew Entered Performance Data",   1, "binary",  0,        1),
]


def _xml_escape(s):
    return (str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def _decode_tele_words(raw_bytes):
    n = len(raw_bytes) // 2
    return list(struct.unpack(f">{n}H", raw_bytes))


def _word_to_float(word, lo, hi):
    raw12 = word & 0x0FFF
    return lo + (raw12 / 4095.0) * (hi - lo)


def _parse_params_from_bin(raw_bytes, duration_sec=60):
    words = _decode_tele_words(raw_bytes)
    result = {}
    idx = 0
    for (name, rate_hz, wf, lo, hi) in PARAM_DEFS[:179]:
        n = int(rate_hz * duration_sec)
        chunk = words[idx: idx + n]
        if chunk:
            floats = [_word_to_float(w, lo, hi) for w in chunk]
            result[name] = {"lo": lo, "hi": hi, "rate": rate_hz,
                            "samples": floats,
                            "first": round(floats[0], 4),
                            "last":  round(floats[-1], 4),
                            "min":   round(min(floats), 4),
                            "max":   round(max(floats), 4),
                            "mean":  round(sum(floats)/len(floats), 4)}
        idx += n
    return result


class XlsxWriter:
    def __init__(self, path):
        self.path    = path
        self.sheets  = []
        self._shared = []
        self._si     = {}

    def _sid(self, s):
        s = str(s)
        if s not in self._si:
            self._si[s] = len(self._shared)
            self._shared.append(s)
        return self._si[s]

    def add_sheet(self, name, rows, col_widths=None):
        self.sheets.append((name, rows, col_widths or []))

    def _cell(self, col, row):
        letters = ""
        c = col + 1
        while c:
            c, r = divmod(c - 1, 26)
            letters = chr(65 + r) + letters
        return f"{letters}{row + 1}"

    def _row_xml(self, row_idx, row_data):
        cells = []
        for ci, val in enumerate(row_data):
            ref = self._cell(ci, row_idx)
            if val is None or val == "":
                continue
            if isinstance(val, bool):
                cells.append(f'<c r="{ref}" t="b"><v>{1 if val else 0}</v></c>')
            elif isinstance(val, (int, float)):
                cells.append(f'<c r="{ref}"><v>{val}</v></c>')
            else:
                sid = self._sid(val)
                cells.append(f'<c r="{ref}" t="s"><v>{sid}</v></c>')
        return f'<row r="{row_idx+1}">{"".join(cells)}</row>'

    def _sheet_xml(self, rows, col_widths):
        col_xml = ""
        if col_widths:
            parts = []
            for i, w in enumerate(col_widths):
                parts.append(f'<col min="{i+1}" max="{i+1}" width="{w}" customWidth="1"/>')
            col_xml = f'<cols>{"".join(parts)}</cols>'

        row_xml = "".join(self._row_xml(ri, r) for ri, r in enumerate(rows))
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'{col_xml}<sheetData>{row_xml}</sheetData></worksheet>'
        )

    def _shared_strings_xml(self):
        n = len(self._shared)
        items = "".join(
            f"<si><t>{_xml_escape(s)}</t></si>" for s in self._shared)
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            f'count="{n}" uniqueCount="{n}">{items}</sst>'
        )

    def _workbook_xml(self):
        sids = "".join(
            f'<sheet name="{_xml_escape(n)}" sheetId="{i+1}" '
            f'r:id="rId{i+1}"/>'
            for i, (n, _, _) in enumerate(self.sheets))
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f'<sheets>{sids}</sheets></workbook>'
        )

    def _wb_rels_xml(self):
        rels = "".join(
            f'<Relationship Id="rId{i+1}" '
            f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{i+1}.xml"/>'
            for i in range(len(self.sheets)))
        rels += (
            f'<Relationship Id="rId{len(self.sheets)+1}" '
            f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" '
            f'Target="sharedStrings.xml"/>'
        )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'{rels}</Relationships>'
        )

    def save(self):
        sheet_xmls = [self._sheet_xml(rows, cw) for _, rows, cw in self.sheets]
        ss_xml     = self._shared_strings_xml()
        wb_xml     = self._workbook_xml()
        rels_xml   = self._wb_rels_xml()

        ct_parts = "".join(
            f'<Override PartName="/xl/worksheets/sheet{i+1}.xml" '
            f'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            for i in range(len(self.sheets)))
        ct = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
            f'{ct_parts}</Types>'
        )
        root_rels = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="xl/workbook.xml"/></Relationships>'
        )

        with zipfile.ZipFile(self.path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml",    ct)
            z.writestr("_rels/.rels",            root_rels)
            z.writestr("xl/workbook.xml",        wb_xml)
            z.writestr("xl/_rels/workbook.xml.rels", rels_xml)
            z.writestr("xl/sharedStrings.xml",   ss_xml)
            for i, xml in enumerate(sheet_xmls):
                z.writestr(f"xl/worksheets/sheet{i+1}.xml", xml)

        print(f"  Saved: {self.path}")


def build_summary_sheet(log):
    rows = [
        ["ARINC-717 FDR + CVR Transmission Report", "", "", ""],
        ["", "", "", ""],
        ["Field", "Value", "", ""],
        ["Ground Station",      log.get("gs_name", "")],
        ["Session ID",          log.get("session_id", "")[:16] + "..."],
        ["Timestamp",           log.get("timestamp", "")],
        ["ECDSA Signature",     "VALID" if log.get("ecdsa_valid") else "INVALID"],
        ["Telemetry Match",     "MATCH" if log.get("tele_match_orig") else "MISMATCH"],
        ["Audio Match",         "MATCH" if log.get("audio_match_orig") else "MISMATCH"],
        ["", "", "", ""],
        ["COMPRESSION", "", "", ""],
        ["Stream", "Raw Bytes", "Compressed Bytes", "Ratio", "Algorithm"],
        ["FDR",
         log.get("fdr_raw_bytes", 0),
         log.get("fdr_comp_bytes", 0),
         log.get("fdr_ratio", 0),
         log.get("fdr_algo", "").upper()],
        ["CVR",
         log.get("cvr_raw_bytes", 0),
         log.get("cvr_comp_bytes", 0),
         log.get("cvr_ratio", 0),
         log.get("cvr_algo", "").upper()],
        ["TOTAL",
         log.get("fdr_raw_bytes", 0) + log.get("cvr_raw_bytes", 0),
         log.get("fdr_comp_bytes", 0) + log.get("cvr_comp_bytes", 0),
         round((log.get("fdr_raw_bytes", 0) + log.get("cvr_raw_bytes", 0)) /
               max(1, log.get("fdr_comp_bytes", 0) + log.get("cvr_comp_bytes", 0)), 3),
         ""],
        ["", "", "", ""],
        ["TRANSMISSION", "", "", ""],
        ["Total Chunks",        log.get("total_chunks", 0)],
        ["Received Chunks",     log.get("received_chunks", 0)],
        ["Wire Bytes",          log.get("wire_bytes_total", 0)],
        ["Transfer Duration s", log.get("transfer_sec", 0)],
        ["Throughput Mbps",     log.get("throughput_mbps", 0)],
        ["Avg Latency ms",      log.get("avg_latency_ms", 0)],
        ["P95 Latency ms",      log.get("p95_latency_ms", 0)],
    ]
    return rows


def build_params_sheet(sent_params, recv_params):
    headers = ["Parameter", "Rate Hz", "Min Range", "Max Range",
               "Sent First", "Sent Last", "Sent Min", "Sent Max", "Sent Mean",
               "Recv First", "Recv Last", "Recv Min", "Recv Max", "Recv Mean",
               "First Match", "Last Match"]
    rows = [headers]
    all_names = list(sent_params.keys())
    for name in all_names:
        sp = sent_params.get(name, {})
        rp = recv_params.get(name, {})
        first_match = abs((sp.get("first", 0) or 0) - (rp.get("first", 0) or 0)) < 0.01
        last_match  = abs((sp.get("last",  0) or 0) - (rp.get("last",  0) or 0)) < 0.01
        rows.append([
            name,
            sp.get("rate", ""),
            sp.get("lo", ""),
            sp.get("hi", ""),
            sp.get("first", ""),
            sp.get("last", ""),
            sp.get("min", ""),
            sp.get("max", ""),
            sp.get("mean", ""),
            rp.get("first", ""),
            rp.get("last", ""),
            rp.get("min", ""),
            rp.get("max", ""),
            rp.get("mean", ""),
            "YES" if first_match else "NO",
            "YES" if last_match  else "NO",
        ])
    return rows


def build_packet_sheet(packets):
    headers = ["Chunk", "Seq", "Timestamp ms", "Recv Time",
               "Latency ms", "Wire Bytes", "Retransmit", "Duplicate", "From"]
    rows = [headers]
    for p in packets:
        rows.append([
            p.get("chunk", ""),
            p.get("seq", ""),
            p.get("ts_ms", ""),
            p.get("recv_t", ""),
            p.get("latency_ms", ""),
            p.get("wire_bytes", ""),
            "YES" if p.get("retx") else "NO",
            "YES" if p.get("dup")  else "NO",
            p.get("from", ""),
        ])
    return rows


def build_chunk_map_sheet(packets, total_chunks):
    headers = ["Chunk Index", "Status", "Retransmit", "Duplicate", "Latency ms"]
    rows    = [headers]
    chunk_map = {}
    for p in packets:
        ci = p.get("chunk")
        if ci is not None and ci not in chunk_map:
            chunk_map[ci] = p
    for i in range(total_chunks):
        p = chunk_map.get(i)
        if p:
            rows.append([i,
                         "RECEIVED",
                         "YES" if p.get("retx") else "NO",
                         "YES" if p.get("dup")  else "NO",
                         p.get("latency_ms", "")])
        else:
            rows.append([i, "MISSING", "", "", ""])
    return rows


def build_latency_sheet(packets):
    headers = ["Chunk", "Latency ms", "Cumulative Avg ms"]
    rows    = [headers]
    running = 0.0
    count   = 0
    for p in packets:
        lat = p.get("latency_ms")
        if lat is not None:
            count   += 1
            running += lat
            rows.append([p.get("chunk", ""), lat, round(running / count, 2)])
    return rows


def find_log_file():
    logs = sorted(glob.glob("output/received/log_*.json"))
    if not logs:
        return None
    return logs[-1]


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Generate Excel report from session log")
    ap.add_argument("--log",    default=None, help="Path to log_*.json (auto-finds latest)")
    ap.add_argument("--sent",   default="output/telemetry_raw.bin")
    ap.add_argument("--recv",   default=None, help="Path to received telemetry .bin (auto-finds)")
    ap.add_argument("--out",    default=None, help="Output .xlsx path (auto-named)")
    ap.add_argument("--dur",    type=int, default=60, help="Simulation duration seconds")
    args = ap.parse_args()

    log_path = args.log or find_log_file()
    if not log_path:
        print("No log file found in output/received/. Run a session first.")
        sys.exit(1)
    print(f"Using log: {log_path}")

    with open(log_path) as f:
        log = json.load(f)

    sent_params = {}
    if os.path.exists(args.sent):
        raw = open(args.sent, "rb").read()
        sent_params = _parse_params_from_bin(raw, args.dur)
        print(f"Sent telemetry  : {args.sent}  ({len(raw):,}B, {len(sent_params)} params)")

    recv_bin = args.recv
    if not recv_bin:
        sid8 = log.get("session_id", "")[:8]
        candidates = glob.glob(f"output/received/telemetry_{sid8}*.bin")
        if candidates:
            recv_bin = candidates[0]

    recv_params = {}
    if recv_bin and os.path.exists(recv_bin):
        raw = open(recv_bin, "rb").read()
        recv_params = _parse_params_from_bin(raw, args.dur)
        print(f"Recv telemetry  : {recv_bin}  ({len(raw):,}B, {len(recv_params)} params)")
    else:
        print("No received telemetry bin found — params sheet will show sent only.")

    packets       = log.get("packets", [])
    total_chunks  = log.get("total_chunks", 0)
    sid8          = log.get("session_id", "unknown")[:8]
    gs            = log.get("gs_name", "GS").replace(" ", "-")
    out_path      = args.out or f"output/report_{sid8}_{gs}.xlsx"

    wb = XlsxWriter(out_path)

    wb.add_sheet("Summary",
                 build_summary_sheet(log),
                 col_widths=[30, 20, 20, 12, 16])

    wb.add_sheet("FDR Parameters",
                 build_params_sheet(sent_params, recv_params),
                 col_widths=[34, 8, 10, 10, 12, 12, 12, 12, 12,
                             12, 12, 12, 12, 12, 12, 12])

    wb.add_sheet("Packet Log",
                 build_packet_sheet(packets),
                 col_widths=[8, 8, 16, 14, 12, 12, 12, 12, 14])

    wb.add_sheet("Chunk Map",
                 build_chunk_map_sheet(packets, total_chunks),
                 col_widths=[14, 12, 12, 12, 14])

    wb.add_sheet("Latency",
                 build_latency_sheet(packets),
                 col_widths=[10, 14, 18])

    wb.save()
    print(f"\nReport ready: {out_path}")
    print(f"  Sheets: Summary | FDR Parameters | Packet Log | Chunk Map | Latency")


if __name__ == "__main__":
    main()
