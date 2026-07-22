from __future__ import annotations

from .. import models as models_mod
from ._util import print_json, strip_noisy_fields, write_json


def register(subparsers):
    model = subparsers.add_parser("model", help="Available LLM models")
    sub = model.add_subparsers(dest="action", required=True)

    p = sub.add_parser("list", help="List active cloud LLM models available to agents")
    p.add_argument("--type", choices=("text", "image"), default=None,
                   help="Filter by model type")
    p.add_argument("--full", action="store_true",
                   help="Include modalities, pricing, and creation metadata")
    p.add_argument("--out", default=None,
                   help="Write the complete model response to this file")
    p.set_defaults(func=run_list)


def _model_summary(model: dict, *, full: bool = False) -> dict:
    row = {
        "display_name": model.get("display_name"),
        "model_id": model.get("model_id"),
        "provider": model.get("provider"),
        "model_type": model.get("model_type"),
    }
    if full:
        row.update({
            "input_modalities": model.get("input_modalities") or [],
            "input_credits_per_million_tokens": model.get("input_credits_per_million_tokens"),
            "output_credits_per_million_tokens": model.get("output_credits_per_million_tokens"),
            "created_at": model.get("created_at"),
        })
    return row


def run_list(args, client) -> int:
    result = models_mod.list_available(client, model_type=args.type)
    full_result = strip_noisy_fields(result)
    write_json(args.out, full_result)
    print_json([_model_summary(model, full=args.full) for model in result])
    return 0
