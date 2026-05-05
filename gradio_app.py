import gradio as gr
from core_agents.master_agent import run_master_agent
from core_agents.supplier_discovery_agent import run_supplier_discovery
from dotenv import load_dotenv

load_dotenv()


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
    message = master_result["message"]
    details = ""

    if master_result["validation_details"]:
        vd = master_result["validation_details"]
        details = f"**Confidence: {vd['confidence_score']}**\n"
        if vd.get("suggested_category"):
            details += f"Suggested Category: {vd['suggested_category']}\n"

    final_output = f"{message}\n\n---\n{details}"

    supplier_md = _format_suppliers(master_result.get("supplier_discovery"))
    show_retry = status == "Ready for Discovery" and not master_result.get("supplier_discovery")

    return status, final_output, gr.update(visible=show_retry), supplier_md


async def retry_supplier_discovery(category, description, quantity):
    try:
        quantity = int(quantity)
    except ValueError:
        return gr.update(visible=True), "Invalid quantity."

    result = await run_supplier_discovery(category, description, quantity)
    supplier_md = _format_suppliers({"suppliers": [s.model_dump() for s in result.suppliers], "search_query": result.search_query})
    return gr.update(visible=False), supplier_md


def _format_suppliers(sd: dict | None) -> str:
    if not sd or not sd.get("suppliers"):
        return ""
    lines = [f"### Suppliers found (query: `{sd.get('search_query', '')}`)"]
    for i, s in enumerate(sd["suppliers"], 1):
        lines.append(f"\n**{i}. {s['name']}**")
        if s.get("website"):
            lines.append(f"- Website: {s['website']}")
        if s.get("contact_email"):
            lines.append(f"- Email: {s['contact_email']}")
        if s.get("phone"):
            lines.append(f"- Phone: {s['phone']}")
        lines.append(f"- {s['relevance_summary']}")
    return "\n".join(lines)


with gr.Blocks(title="SME Procurement - BOM Validation") as demo:
    gr.Markdown("# SME Procurement Platform - BOM Validation")
    gr.Markdown("Enter the details of a part to validate its sourcability using the BOM Input Agent.")

    with gr.Row():
        with gr.Column():
            cat_input = gr.Textbox(label="Category", placeholder="e.g., Electronics, Fasteners, Custom CNC")
            desc_input = gr.Textbox(label="SKU or Description", lines=3, placeholder="e.g., 10k Ohm 0402 Resistor, 1% tolerance")
            qty_input = gr.Number(label="Quantity", value=100)
            submit_btn = gr.Button("Validate Part", variant="primary")

        with gr.Column():
            status_output = gr.Textbox(label="Validation Status", interactive=False)
            details_output = gr.Markdown(label="Agent Reasoning")

    retry_btn = gr.Button("Retry Supplier Discovery", variant="secondary", visible=False)
    suppliers_output = gr.Markdown(label="Supplier Results")

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
