"""Manfred (getmanfred.com)."""

from .base import fetch_json, job


def src_manfred(cfg, log):
    out = []
    for o in fetch_json("https://www.getmanfred.com/api/v2/public/offers?lang=ES&onlyActive=true"):
        rp = o.get("remotePercentage") or 0
        locs = ", ".join(o.get("locations") or [])
        loc = "Remoto" if rp >= 100 else f"{locs} (híbrido, {rp}% teletrabajo)" if locs else f"Híbrido, {rp}% teletrabajo"
        sal = f"{o.get('salaryFrom') or '?'}–{o.get('salaryTo')} {o.get('currency', '€')}" if o.get("salaryTo") else ""
        desc = f"Teletrabajo: {rp}%.\n" + "\n".join(o.get("highlights") or [])
        out.append(job("manfred", o["id"], o.get("position"), (o.get("company") or {}).get("name"), loc,
                       f"https://www.getmanfred.com/ofertas-empleo/{o['id']}/{o.get('slug', '')}",
                       desc, o.get("updatedAt"), sal, remote=rp >= 100, spain=True))
    return out
