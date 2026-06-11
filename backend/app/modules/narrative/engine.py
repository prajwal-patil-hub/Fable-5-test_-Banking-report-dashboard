"""Executive Intelligence (narrative) engine.

Generates consulting-grade commentary deterministically from warehouse facts,
YoY movements and peer positioning — every sentence traces to a number and a
threshold, so the output is auditable in a way generative text is not. An LLM
layer can later *polish phrasing* on top of these facts, but findings,
takeaways and recommendations are computed, not imagined.

Structure follows the consulting storytelling framework:
  headline (what happened) → commentary (why / so what) →
  takeaways (diagnostic bullets) → recommendations (what to do next).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Bank
from app.modules.benchmarking.engine import bank_position
from app.modules.kpi_warehouse import service as warehouse


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


class _Facts:
    """Lookup helper over the bank-year KPI payload."""

    def __init__(self, db: Session, bank: Bank, fy: str):
        self.db, self.bank, self.fy = db, bank, fy
        payload = warehouse.kpi_payload(db, bank, fy)
        self.kpis = {k["kpi_code"]: k for k in payload["kpis"]}

    def value(self, code: str) -> float | None:
        k = self.kpis.get(code)
        return k["value"] if k else None

    def yoy(self, code: str) -> float | None:
        k = self.kpis.get(code)
        return k["yoy_change"] if k else None

    def yoy_pct(self, code: str) -> float | None:
        k = self.kpis.get(code)
        return k["yoy_change_pct"] if k else None

    def rank(self, code: str) -> dict | None:
        return bank_position(self.db, self.bank.id, code, self.fy)


def _trend_word(delta: float | None, *, good_up: bool = True,
                up: str = "improved", down: str = "declined", flat: str = "held steady",
                threshold: float = 0.05) -> str:
    if delta is None or abs(delta) < threshold:
        return flat
    rising = delta > 0
    return up if rising == good_up else down


def _financial_section(f: _Facts) -> dict:
    roe, roe_d = f.value("roe"), f.yoy("roe")
    nim, nim_d = f.value("nim"), f.yoy("nim")
    pat, pat_pct = f.value("pat"), f.yoy_pct("pat")
    cti, cti_d = f.value("cost_to_income"), f.yoy("cost_to_income")
    pos = f.rank("roe")

    headline_bits = []
    if pat is not None and pat_pct is not None:
        verb = "grew" if pat_pct >= 0 else "contracted"
        headline_bits.append(f"PAT {verb} {abs(pat_pct):.1f}% YoY to ₹{pat:,.0f} Cr")
    if roe is not None:
        headline_bits.append(f"ROE at {roe:.1f}%")
    headline = ("; ".join(headline_bits) or "Financial performance overview") + (
        f", {_ordinal(pos['rank'])} of {pos['peer_count']} peers" if pos else "")

    commentary = []
    if roe is not None and roe_d is not None:
        commentary.append(
            f"Return on equity {_trend_word(roe_d, up='expanded', down='compressed')} "
            f"{abs(roe_d) * 100:.0f} bps year-over-year to {roe:.1f}%.")
    if nim is not None:
        commentary.append(
            f"Margins {_trend_word(nim_d, up='widened', down='narrowed')} with NIM at {nim:.2f}%, "
            f"{'a tailwind' if (nim_d or 0) >= 0 else 'a headwind'} for core earnings.")
    if cti is not None:
        eff = "improving operating leverage" if (cti_d or 0) <= 0 else "rising cost intensity"
        commentary.append(f"Cost-to-income stands at {cti:.1f}%, reflecting {eff}.")

    takeaways = []
    if pos:
        takeaways.append(
            f"Profitability ranks {_ordinal(pos['rank'])} among {pos['peer_count']} peers "
            f"(ROE percentile {pos['percentile']:.0f}).")
    if nim is not None and (nim_d or 0) < 0:
        takeaways.append("Margin compression is the principal drag on earnings momentum.")
    if cti is not None and cti > 50:
        takeaways.append("Cost base remains above the 50% efficiency frontier typical of "
                         "best-in-class franchises.")

    recommendations = []
    if cti is not None and cti > 50:
        recommendations.append("Prioritise a structured cost programme: branch-format "
                               "rationalisation and digital-led servicing migration.")
    if nim is not None and (nim_d or 0) < 0:
        recommendations.append("Defend NIM through deposit-mix management (CASA mobilisation) "
                               "and disciplined loan pricing.")

    return {"module": "financial", "headline": headline,
            "commentary": " ".join(commentary) or "Insufficient financial data for this period.",
            "takeaways": takeaways, "recommendations": recommendations}


def _asset_quality_section(f: _Facts) -> dict:
    gnpa_r, gnpa_d = f.value("gnpa_ratio"), f.yoy("gnpa_ratio")
    nnpa_r = f.value("nnpa_ratio")
    pcr = f.value("pcr")
    pos = f.rank("gnpa_ratio")

    quality = ("benign" if gnpa_r is not None and gnpa_r < 2 else
               "manageable" if gnpa_r is not None and gnpa_r < 4 else
               "elevated" if gnpa_r is not None else "unassessed")
    headline = (f"Asset quality {quality}: GNPA at {gnpa_r:.2f}%"
                + (f", {_trend_word(gnpa_d, good_up=False, up='deteriorating', down='improving')} YoY"
                   if gnpa_d is not None else "")) if gnpa_r is not None else "Asset quality overview"

    commentary = []
    if gnpa_r is not None and gnpa_d is not None:
        verb = "improved" if gnpa_d < 0 else "slipped"
        commentary.append(f"Headline GNPA {verb} {abs(gnpa_d) * 100:.0f} bps to {gnpa_r:.2f}%.")
    if nnpa_r is not None and pcr is not None:
        cushion = "a strong provisioning cushion" if pcr >= 70 else "a thin provisioning cushion"
        commentary.append(f"Net NPA of {nnpa_r:.2f}% against PCR of {pcr:.1f}% indicates {cushion}.")

    takeaways = []
    if pos:
        takeaways.append(f"Asset quality ranks {_ordinal(pos['rank'])} of {pos['peer_count']} "
                         f"peers on GNPA.")
    if pcr is not None and pcr < 70:
        takeaways.append("Provision coverage below the 70% prudential comfort level.")

    recommendations = []
    if pcr is not None and pcr < 70:
        recommendations.append("Accelerate provisioning to lift PCR above 70% before credit-cycle "
                               "normalisation erodes optionality.")
    if gnpa_r is not None and gnpa_d is not None and gnpa_d > 0:
        recommendations.append("Tighten early-warning frameworks on incremental slippages; "
                               "review sector concentration in the watchlist book.")

    return {"module": "asset_quality", "headline": headline,
            "commentary": " ".join(commentary) or "Insufficient asset-quality data for this period.",
            "takeaways": takeaways, "recommendations": recommendations}


def _capital_section(f: _Facts) -> dict:
    cet1, crar, crar_d = f.value("cet1_ratio"), f.value("crar"), f.yoy("crar")
    pos = f.rank("crar")

    strength = ("comfortable" if crar is not None and crar >= 15 else
                "adequate" if crar is not None and crar >= 12.5 else
                "tight" if crar is not None else "unassessed")
    headline = (f"Capital position {strength}: CRAR {crar:.1f}%"
                + (f", CET1 {cet1:.1f}%" if cet1 is not None else "")) \
        if crar is not None else "Capital adequacy overview"

    commentary = []
    if crar is not None:
        buffer = crar - 11.5
        commentary.append(
            f"CRAR of {crar:.1f}% provides a {buffer:.1f}pp buffer over the Basel III India "
            f"minimum (incl. CCB), {_trend_word(crar_d, up='building', down='consuming')} "
            f"capital year-over-year.")
    if cet1 is not None:
        commentary.append(f"Core capital quality is high with CET1 at {cet1:.1f}% of RWA.")

    takeaways = []
    if pos:
        takeaways.append(f"Capitalisation ranks {_ordinal(pos['rank'])} of {pos['peer_count']} peers.")
    recommendations = []
    if crar is not None and crar < 13:
        recommendations.append("Evaluate capital-raise timing and RWA-optimisation levers "
                               "(risk-transfer, portfolio mix) to restore strategic headroom.")
    elif crar is not None and crar >= 16:
        recommendations.append("Surplus capital supports either accelerated growth deployment "
                               "or a review of distribution policy.")

    return {"module": "capital", "headline": headline,
            "commentary": " ".join(commentary) or "Insufficient capital data for this period.",
            "takeaways": takeaways, "recommendations": recommendations}


def _liquidity_section(f: _Facts) -> dict:
    casa, casa_d = f.value("casa_ratio"), f.yoy("casa_ratio")
    lcr = f.value("lcr")
    dep_g, loan_g = f.value("deposit_growth"), f.value("loan_growth")

    headline = (f"Funding profile: CASA {casa:.1f}%"
                + (f", deposits {dep_g:+.1f}% YoY" if dep_g is not None else "")) \
        if casa is not None else "Liquidity & funding overview"

    commentary = []
    if casa is not None:
        quality = "low-cost funding advantage" if casa >= 40 else "reliance on term funding"
        commentary.append(
            f"CASA ratio of {casa:.1f}% ({_trend_word(casa_d)} YoY) reflects a {quality}.")
    if lcr is not None:
        commentary.append(f"LCR of {lcr:.0f}% sits well clear of the 100% regulatory floor."
                          if lcr >= 110 else
                          f"LCR of {lcr:.0f}% leaves limited headroom over the 100% floor.")
    if dep_g is not None and loan_g is not None:
        gap = loan_g - dep_g
        if gap > 3:
            commentary.append(f"Credit growth ({loan_g:.1f}%) is outpacing deposit growth "
                              f"({dep_g:.1f}%), pressuring the funding gap.")
        else:
            commentary.append(f"Deposit growth ({dep_g:.1f}%) is keeping pace with credit "
                              f"expansion ({loan_g:.1f}%).")

    takeaways = []
    if casa is not None and (casa_d or 0) < 0:
        takeaways.append("CASA attrition raises the marginal cost of funds — an industry-wide "
                         "deposit-competition dynamic.")
    recommendations = []
    if dep_g is not None and loan_g is not None and loan_g - dep_g > 3:
        recommendations.append("Rebalance growth: granular retail-deposit mobilisation ahead of "
                               "further credit expansion to protect NIM and LCR.")

    return {"module": "liquidity", "headline": headline,
            "commentary": " ".join(commentary) or "Insufficient liquidity data for this period.",
            "takeaways": takeaways, "recommendations": recommendations}


def _operations_section(f: _Facts) -> dict:
    branches, employees = f.value("branches"), f.value("employees")
    digital, digital_d = f.value("digital_txn_share"), f.yoy("digital_txn_share")

    headline = (f"Digital share at {digital:.0f}% of transactions"
                if digital is not None else "Operations overview")
    commentary = []
    if digital is not None:
        commentary.append(
            f"Digital channels handle {digital:.0f}% of transactions"
            + (f", up {digital_d:.0f}pp YoY" if digital_d and digital_d > 0 else "") + ".")
    if branches is not None and employees is not None:
        commentary.append(f"The physical network spans {branches:,.0f} branches with "
                          f"{employees:,.0f} employees.")

    takeaways, recommendations = [], []
    if digital is not None and digital < 80:
        recommendations.append("Push digital adoption past the 80% threshold where branch-format "
                               "economics can be structurally reset.")

    return {"module": "operations", "headline": headline,
            "commentary": " ".join(commentary) or "Insufficient operations data for this period.",
            "takeaways": takeaways, "recommendations": recommendations}


def _benchmarking_section(f: _Facts) -> dict:
    positions = []
    for code, label in (("roe", "profitability"), ("gnpa_ratio", "asset quality"),
                        ("crar", "capitalisation"), ("casa_ratio", "funding")):
        pos = f.rank(code)
        if pos:
            positions.append((label, pos))
    if not positions:
        return {"module": "benchmarking", "headline": "Peer benchmarking",
                "commentary": "No peer data available for this period.",
                "takeaways": [], "recommendations": []}

    strong = [p for p in positions if p[1]["percentile"] >= 50]
    weak = [p for p in positions if p[1]["percentile"] < 50]
    headline = (f"Peer positioning: top-half on {len(strong)} of {len(positions)} "
                f"strategic dimensions")
    commentary_parts = [
        f"{label.capitalize()} ranks {_ordinal(p['rank'])} of {p['peer_count']}"
        for label, p in positions
    ]
    takeaways = []
    if strong:
        takeaways.append("Relative strengths: " + ", ".join(label for label, _ in strong) + ".")
    if weak:
        takeaways.append("Competitive gaps: " + ", ".join(label for label, _ in weak) + ".")
    recommendations = []
    if weak:
        recommendations.append(
            "Close the gap to peer median on " + " and ".join(label for label, _ in weak)
            + " — these dimensions weigh most on relative valuation.")

    return {"module": "benchmarking", "headline": headline,
            "commentary": "; ".join(commentary_parts) + ".",
            "takeaways": takeaways, "recommendations": recommendations}


def build_narrative(db: Session, bank: Bank, fy: str) -> dict:
    f = _Facts(db, bank, fy)
    sections = [
        _financial_section(f),
        _asset_quality_section(f),
        _capital_section(f),
        _liquidity_section(f),
        _operations_section(f),
        _benchmarking_section(f),
    ]

    # Executive summary = strongest signal from each domain (level-1 storytelling)
    summary: list[str] = []
    for s in sections:
        if s["takeaways"]:
            summary.append(s["takeaways"][0])
        elif s["headline"] and "overview" not in s["headline"].lower():
            summary.append(s["headline"] + ".")
    return {
        "bank": {"id": bank.id, "code": bank.code, "name": bank.name},
        "fiscal_year": fy,
        "executive_summary": summary[:6],
        "sections": sections,
    }
