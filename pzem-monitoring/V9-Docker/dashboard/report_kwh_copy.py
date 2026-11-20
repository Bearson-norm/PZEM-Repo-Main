"""
Teks penjelasan perbandingan kWh (web + PDF) — satu sumber agar tidak drift.
"""

KWH_COMPARISON_HELP_TITLE = "Cara membaca Selisih & Perubahan"

# HTML ringkas untuk ReportLab Paragraph (pakai <br/>)
KWH_COMPARISON_HELP_HTML = """
<b>Cara membaca Selisih &amp; Perubahan</b><br/>
&bull; Semua angka kWh adalah <b>konsumsi</b> (penggunaan listrik), bukan arah aliran ke jaringan.<br/>
&bull; <b>Selisih</b> = kWh periode terpilih dikurangi kWh periode sebelumnya (durasi sama, langsung sebelum rentang Anda).<br/>
&bull; <b>Minus (&minus;)</b> = konsumsi lebih rendah daripada periode pembanding (hemat / beban turun). <b>Bukan</b> listrik yang dikembalikan ke PLN atau sumber.<br/>
&bull; <b>Plus (+)</b> = konsumsi lebih tinggi daripada periode pembanding.<br/>
&bull; Warna: hijau = turun, merah = naik (dibanding periode sebelumnya).
"""

# Bullet list untuk halaman web (teks polos per item)
KWH_COMPARISON_HELP_LINES = [
    "Semua angka kWh adalah konsumsi (penggunaan listrik), bukan arah aliran ke jaringan.",
    "Selisih = kWh periode terpilih dikurangi kWh periode sebelumnya (durasi sama, langsung sebelum rentang Anda).",
    "Minus (−) = konsumsi lebih rendah daripada periode pembanding (hemat / beban turun). Bukan listrik yang dikembalikan ke PLN atau sumber.",
    "Plus (+) = konsumsi lebih tinggi daripada periode pembanding.",
    "Warna: hijau = turun, merah = naik (dibanding periode sebelumnya).",
]


def _fmt_dt_id(value):
    if value is None:
        return "—"
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%Y %H:%M")
    s = str(value).replace("T", " ")[:16]
    try:
        from datetime import datetime

        if "T" in str(value):
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if dt.tzinfo:
                dt = dt.replace(tzinfo=None)
            return dt.strftime("%d/%m/%Y %H:%M")
    except (ValueError, TypeError):
        pass
    return s


def format_delta_interpretation(delta_kwh, change_percent, prev_start, prev_end):
    """Kalimat singkat interpretasi selisih total (plain text)."""
    delta = float(delta_kwh or 0)
    pct = float(change_percent or 0)
    prev_label = f"{_fmt_dt_id(prev_start)} – {_fmt_dt_id(prev_end)}"
    abs_kwh = abs(delta)
    kwh_str = f"{abs_kwh:.3f}"
    pct_str = f"{abs(pct):.1f}"

    if delta < 0:
        return (
            f"Konsumsi turun {kwh_str} kWh ({pct_str}%) dibanding periode pembanding "
            f"({prev_label}). Angka minus tidak berarti arus balik ke sumber."
        )
    if delta > 0:
        return (
            f"Konsumsi naik {kwh_str} kWh (+{pct_str}%) dibanding periode pembanding "
            f"({prev_label})."
        )
    return f"Konsumsi sama dengan periode pembanding ({prev_label})."