import gradio as gr
from core_agents.master_agent import run_master_agent
from core_agents.supplier_discovery_agent import run_supplier_discovery
from dotenv import load_dotenv

load_dotenv()

CSS = """
body, .gradio-container { background: #0f172a !important; }

.header-section {
    text-align: center;
    padding: 2rem 1rem 1rem;
    border-bottom: 1px solid #1e293b;
    margin-bottom: 1.5rem;
}
.header-section h1 {
    font-size: 1.75rem;
    font-weight: 700;
    color: #f1f5f9;
    margin-bottom: 0.25rem;
}
.header-section p { color: #64748b; font-size: 0.95rem; margin: 0; }

.card {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.3);
}

.section-label {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #475569;
    margin-bottom: 0.75rem;
}

#submit-btn {
    background: #3b82f6;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    font-size: 0.95rem;
    transition: background 0.15s;
    width: 100%;
    margin-top: 0.5rem;
}
#submit-btn:hover { background: #2563eb; }

#retry-btn {
    border: 1px solid #334155;
    border-radius: 8px;
    color: #94a3b8;
    font-size: 0.875rem;
    margin-top: 0.75rem;
    background: transparent;
}

.suppliers-section {
    margin-top: 1.5rem;
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.3);
}

footer { display: none !important; }
"""


async def process_bom_item(category, description, quantity):
    if not category or not description:
        return "Error", "Category and Description are required.", gr.update(visible=False), ""
    try:
        quantity = int(quantity)
        if quantity <= 0:
            return "Error", "Quantity must be greater than 0.", gr.update(visible=False), ""
    except ValueError:
        return "Error", "Quantity must be a valid integer.", gr.update(visible=False), ""

    master_result = await run_master_agent(category, description, quantity)

    status = master_result["status"]
    vd = master_result.get("validation_details") or {}

    lines = []
    if vd.get("confidence_score") is not None:
        score = vd["confidence_score"]
        color = "#16a34a" if score >= 0.75 else "#dc2626"
        lines.append(f'<span style="color:{color};font-weight:600;">Confidence: {score:.0%}</span>')
    if vd.get("reasoning"):
        lines.append(f"**Reasoning:** {vd['reasoning']}")
    if vd.get("suggested_category"):
        lines.append(f"**Suggested Category:** {vd['suggested_category']}")
    validation_md = "\n\n".join(lines)

    supplier_md = _format_suppliers(master_result.get("supplier_discovery"))
    show_retry = status == "Ready for Discovery" and not master_result.get("supplier_discovery")

    return status, validation_md, gr.update(visible=show_retry), supplier_md


async def retry_supplier_discovery(category, description, quantity):
    try:
        quantity = int(quantity)
    except ValueError:
        return gr.update(visible=True), "Invalid quantity."

    result = await run_supplier_discovery(category, description, quantity)
    supplier_md = _format_suppliers({
        "suppliers": [s.model_dump() for s in result.suppliers],
        "search_query": result.search_query,
    })
    return gr.update(visible=False), supplier_md


def _format_suppliers(sd: dict | None) -> str:
    if not sd or not sd.get("suppliers"):
        return ""
    rows = []
    for s in sd["suppliers"]:
        name = f"**{s['name']}**"
        website = f"[↗ Visit]({s['website']})" if s.get("website") else "—"
        email = s.get("contact_email") or "—"
        phone = s.get("phone") or "—"
        notes = s.get("relevance_summary", "")
        rows.append(f"| {name} | {website} | {email} | {phone} | {notes} |")

    header = "| Supplier | Website | Email | Phone | Why a match |\n|----------|---------|-------|-------|-------------|"
    query = sd.get("search_query", "")
    return f'<div class="section-label">Supplier Results</div>\n\n*Query: `{query}`*\n\n{header}\n' + "\n".join(rows)


theme = gr.themes.Soft(
    primary_hue="blue",
    neutral_hue="slate",
    font=gr.themes.GoogleFont("Inter"),
).set(
    body_background_fill="#0f172a",
    body_background_fill_dark="#0f172a",
    block_background_fill="#1e293b",
    block_background_fill_dark="#1e293b",
    block_border_color="#334155",
    block_border_color_dark="#334155",
    block_border_width="1px",
    block_radius="12px",
    block_shadow="0 1px 4px rgba(0,0,0,0.3)",
    input_background_fill="#0f172a",
    input_background_fill_dark="#0f172a",
    input_border_color="#334155",
    input_border_color_dark="#334155",
    input_border_width="1px",
    input_radius="8px",
    body_text_color="#e2e8f0",
    body_text_color_dark="#e2e8f0",
    block_label_text_color="#94a3b8",
    block_label_text_color_dark="#94a3b8",
)

FORCE_DARK = "() => { document.documentElement.classList.add('dark'); }"

with gr.Blocks(title="ProcureAI", theme=theme, css=CSS, js=FORCE_DARK) as demo:
    with gr.Column(elem_classes="header-section"):
        gr.Markdown("# ProcureAI")
        gr.Markdown("AI-powered procurement automation for SMEs — validate BOM items and discover suppliers instantly.")

    with gr.Row(equal_height=True):
        with gr.Column(scale=1, elem_classes="card"):
            gr.Markdown('<div class="section-label">BOM Item Details</div>')
            cat_input = gr.Textbox(
                label="Category",
                placeholder="e.g., Electronics, Fasteners, Custom CNC",
                container=True,
            )
            desc_input = gr.Textbox(
                label="SKU or Description",
                lines=3,
                placeholder="e.g., 10k Ohm 0402 SMD Resistor, 1% tolerance, 0.1W",
            )
            qty_input = gr.Number(label="Quantity", value=100)
            submit_btn = gr.Button("Validate & Find Suppliers →", variant="primary", elem_id="submit-btn")

        with gr.Column(scale=1, elem_classes="card"):
            gr.Markdown('<div class="section-label">Validation Result</div>')
            status_output = gr.Textbox(label="Status", interactive=False)
            details_output = gr.Markdown()
            retry_btn = gr.Button("↻ Retry Supplier Discovery", variant="secondary", visible=False, elem_id="retry-btn")

    with gr.Column(elem_classes="suppliers-section"):
        suppliers_output = gr.Markdown()

    submit_btn.click(
        fn=process_bom_item,
        inputs=[cat_input, desc_input, qty_input],
        outputs=[status_output, details_output, retry_btn, suppliers_output],
    )

    retry_btn.click(
        fn=retry_supplier_discovery,
        inputs=[cat_input, desc_input, qty_input],
        outputs=[retry_btn, suppliers_output],
    )

if __name__ == "__main__":
    demo.launch()
