import gradio as gr
from core_agents.master_agent import run_master_agent
from dotenv import load_dotenv

# Load environment variables (like OPENAI_API_KEY)
load_dotenv()

async def process_bom_item(category, description, quantity):
    if not category or not description:
        return "Error", "Category and Description are required."
    
    try:
        quantity = int(quantity)
        if quantity <= 0:
            return "Error", "Quantity must be greater than 0."
    except ValueError:
        return "Error", "Quantity must be a valid integer."

    # Call the Master Agent
    master_result = await run_master_agent(category, description, quantity)
    
    status = master_result["status"]
    message = master_result["message"]
    details = ""
    
    if master_result["validation_details"]:
        vd = master_result["validation_details"]
        details = f"**Agent Tool Output (Confidence: {vd['confidence_score']})**\n"
        if vd.get("suggested_category"):
            details += f"Suggested Category: {vd['suggested_category']}\n"
    
    final_output = f"{message}\n\n---\n{details}"
    
    return status, final_output

# Define the Gradio Interface
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
            
    submit_btn.click(
        fn=process_bom_item,
        inputs=[cat_input, desc_input, qty_input],
        outputs=[status_output, details_output]
    )

if __name__ == "__main__":
    demo.launch()
