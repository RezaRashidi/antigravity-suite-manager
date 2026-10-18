"""
CLI entry point for Antigravity Icon Generator.
"""

from __future__ import annotations

import argparse
import sys
from antigravity_suite.icon.gen_config import COLOR_CHOICES, load_icon_config, save_icon_config
from antigravity_suite.icon.gen_custom import generate_custom_instance_icon
from antigravity_suite.icon.gen_masters import ensure_scale_binary, load_master_icons
from antigravity_suite.icon.gen_suite import generate_suite_icons


def build_parser(cfg: dict[str, str]) -> argparse.ArgumentParser:
    """Constructs the CLI argument parser with loaded defaults."""
    parser = argparse.ArgumentParser(description="Antigravity Icon Generator")
    parser.add_argument("--acc1", choices=["black", "white"], default=cfg.get("ACC1_ICON_THEME", "black"))
    parser.add_argument("--acc1-color", choices=COLOR_CHOICES, default=cfg.get("ACC1_EMBLEM_COLOR", "original"))
    parser.add_argument("--acc2", choices=["black", "white"], default=cfg.get("ACC2_ICON_THEME", "black"))
    parser.add_argument("--acc2-color", choices=COLOR_CHOICES, default=cfg.get("ACC2_EMBLEM_COLOR", "violet"))
    parser.add_argument("--acc2-recolor", choices=["true", "false", "1", "0"], default=cfg.get("ACC2_RECOLOR", "true"))
    parser.add_argument("--ide", choices=["black", "white"], default=cfg.get("IDE_ICON_THEME", "white"))
    parser.add_argument("--ide-color", choices=COLOR_CHOICES, default=cfg.get("IDE_EMBLEM_COLOR", "original"))
    parser.add_argument("--save-config", action="store_true", help="Persist chosen options into icons.conf")
    parser.add_argument("--custom-instance", help="Generate icons for a custom instance name")
    parser.add_argument("--custom-theme", choices=["black", "white"], default="black")
    parser.add_argument("--custom-hue", type=float, default=None)
    return parser


def main() -> int:
    """Main execution function for icon generation CLI."""
    cfg = load_icon_config()
    parser = build_parser(cfg)
    args = parser.parse_args()

    acc1_t, acc1_c = args.acc1.lower(), args.acc1_color.lower()
    acc2_t = args.acc2.lower()
    has_acc2_c = any(arg.startswith("--acc2-color") for arg in sys.argv)
    if not has_acc2_c and args.acc2_recolor.lower() in ["false", "0", "no"]:
        acc2_c = "original"
    else:
        acc2_c = args.acc2_color.lower() if args.acc2_color else ("violet" if args.acc2_recolor.lower() in ["true", "1", "yes"] else "original")
    ide_t, ide_c = args.ide.lower(), args.ide_color.lower()

    if args.save_config:
        save_icon_config(acc1_t, acc1_c, acc2_t, acc2_c, "true" if acc2_c != "original" else "false", ide_t, ide_c)

    ensure_scale_binary()
    r_blk, r_wht = load_master_icons()
    if not r_blk:
        print("[ERROR] Master black icon not found.")
        return 1

    if args.custom_instance:
        generate_custom_instance_icon(args.custom_instance, args.custom_theme.lower(), args.custom_hue, r_blk, r_wht)
        return 0

    print(f"[INFO] Settings: App1={acc1_t} ({acc1_c}), App2={acc2_t} ({acc2_c}), IDE={ide_t} ({ide_c})")
    generate_suite_icons(acc1_t, acc1_c, acc2_t, acc2_c, ide_t, ide_c, r_blk, r_wht)
    return 0
