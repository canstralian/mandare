from runtime.execution_record import ExecutionRecord
from runtime.provider_registry import ProviderRegistry
from runtime.evidence_bundle import EvidenceBundle

import gradio as gr
import json
import time


def run(prompt):
    start = time.time()

    provider = ProviderRegistry.get("mock")
    response = provider.invoke(prompt)

    latency = round((time.time() - start) * 1000, 2)

    record = ExecutionRecord.create(
        provider=provider.name,
        intent=prompt,
        context=prompt,
        response=response,
        latency_ms=latency,
    )

    bundle = EvidenceBundle.from_execution(record)

    return (
        json.dumps(record.to_dict(), indent=2),
        json.dumps(bundle.context, indent=2),
        json.dumps(bundle.evidence, indent=2),
        json.dumps(bundle.telemetry, indent=2),
        json.dumps(bundle.replay, indent=2),
        response,
    )


with gr.Blocks(title="RIF Runtime") as demo:
    gr.Markdown("# ⚡ KAT-Coder × RIF Runtime")

    prompt = gr.Textbox(
        label="Intent",
        placeholder="Describe your task..."
    )

    execute = gr.Button("Execute")

    outputs = [
        gr.Code(label="ExecutionRecord", language="json"),
        gr.Code(label="Context", language="json"),
        gr.Code(label="Evidence", language="json"),
        gr.Code(label="Telemetry", language="json"),
        gr.Code(label="Replay", language="json"),
        gr.Textbox(label="Response"),
    ]

    execute.click(
        run,
        inputs=prompt,
        outputs=outputs,
    )

demo.launch()
