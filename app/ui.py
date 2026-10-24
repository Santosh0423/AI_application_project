"""Gradio user interface (presentation layer).

The UI talks only to the AI service layer (src/services/ai_service.py) and the
profile store; it never calls Ollama or the model client directly.
"""

from __future__ import annotations

from typing import Callable

import gradio as gr

from src.services.ai_service import AIService
from src.capabilities.memory import (
    CITIZENSHIP_OPTIONS,
    STAY_OPTIONS,
    STUDENT_TYPE_OPTIONS,
    ProfileStore,
    UserProfile,
)

EXAMPLES = [
    "Can I work while studying in Finland? How many hours?",
    "How do I extend my student residence permit?",
    "Do I need to register my address with DVV?",
    "How do I get a tax card?",
    "Am I covered by Kela as an international student?",
]

INTRO = """# Finland Bureaucracy Helper
Ask about **residence permits, DVV registration, Kela, tax cards and working rights**.
Answers come only from official sources (Migri, DVV, Kela, Vero, InfoFinland) and show where the information comes from.

> **Note:** General guidance only, **not legal advice**. Always confirm with the official authority."""


def build_ui(
    assistant: AIService,
    profile_store: ProfileStore,
    status_check: Callable[[], str],
) -> gr.Blocks:
    initial = profile_store.load()

    def respond(message: str, chat: list[dict], history: list[tuple[str, str]],
                citizenship: str, student_type: str, stay: str, city: str):
        message = (message or "").strip()
        if not message:
            return "", chat, history
        profile = UserProfile(citizenship, student_type, stay, city)
        result = assistant.answer(message, profile, history)
        chat = chat + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": result.to_markdown()},
        ]
        if result.status == "answered":
            history = history + [(message, result.answer)]
        return "", chat, history

    def save_profile(citizenship: str, student_type: str, stay: str, city: str) -> str:
        profile = UserProfile(citizenship, student_type, stay, city)
        try:
            profile_store.save(profile)
        except OSError as exc:
            return f"Error: could not save profile: {exc}"
        return f"Profile saved: {profile.describe()}"

    def clear():
        return [], [], ""

    with gr.Blocks(title="Finland Bureaucracy Helper", analytics_enabled=False) as demo:
        gr.Markdown(INTRO)
        history_state = gr.State([])

        with gr.Row():
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(
                    label="Conversation",
                    height=520,
                    placeholder="Ask a question about Finnish bureaucracy, or pick an example below.",
                )
                with gr.Row():
                    question = gr.Textbox(
                        placeholder="e.g. How do I extend my residence permit?",
                        show_label=False,
                        scale=5,
                        max_lines=4,
                    )
                    send = gr.Button("Ask", variant="primary", scale=1)
                gr.Examples(EXAMPLES, inputs=question, label="Example questions")
                clear_btn = gr.Button("Clear conversation")

            with gr.Column(scale=1):
                gr.Markdown("### Your situation\nAnswers are tailored to this profile. It is saved on this computer only.")
                citizenship = gr.Dropdown(CITIZENSHIP_OPTIONS, value=initial.citizenship, label="Citizenship")
                student_type = gr.Dropdown(STUDENT_TYPE_OPTIONS, value=initial.student_type, label="Status")
                stay = gr.Dropdown(STAY_OPTIONS, value=initial.stay_length, label="Planned stay in Finland")
                city = gr.Textbox(value=initial.city, label="City (optional)", max_lines=1)
                save_btn = gr.Button("Save profile")
                profile_msg = gr.Markdown()

                gr.Markdown("### System status")
                status = gr.Markdown(status_check())
                refresh = gr.Button("Check again", size="sm")

        profile_inputs = [citizenship, student_type, stay, city]
        submit_args = dict(
            fn=respond,
            inputs=[question, chatbot, history_state, *profile_inputs],
            outputs=[question, chatbot, history_state],
        )
        question.submit(**submit_args)
        send.click(**submit_args)
        clear_btn.click(clear, outputs=[chatbot, history_state, question])
        save_btn.click(save_profile, inputs=profile_inputs, outputs=profile_msg)
        refresh.click(lambda: status_check(), outputs=status)

    return demo
