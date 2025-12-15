"""Streamlit chat interface for Digital Twin."""

import streamlit as st

from src.config import settings
from src.llm import get_available_providers
from src.rag import RAGEngine
from src.storage import ChatHistory

# Page config
st.set_page_config(
    page_title="Digital Twin",
    page_icon="🧠",
    layout="wide",
)


def init_session_state():
    """Initialize session state variables."""
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = ChatHistory()

    if "rag_engine" not in st.session_state:
        st.session_state.rag_engine = RAGEngine(
            chat_history=st.session_state.chat_history
        )

    if "current_conversation_id" not in st.session_state:
        st.session_state.current_conversation_id = None

    if "messages" not in st.session_state:
        st.session_state.messages = []


def render_sidebar():
    """Render the sidebar with settings and conversation list."""
    with st.sidebar:
        st.title("🧠 Digital Twin")
        st.markdown("---")

        # LLM Provider selection
        st.subheader("LLM Provider")
        providers = get_available_providers()
        available_providers = [p for p in providers if p["available"]]

        if not available_providers:
            st.warning("No LLM providers available. Configure API keys in .env")
            provider_names = [p["id"] for p in providers]
        else:
            provider_names = [p["id"] for p in available_providers]

        current_provider = settings.llm_provider
        if current_provider not in provider_names and provider_names:
            current_provider = provider_names[0]

        selected_provider = st.selectbox(
            "Select provider",
            options=provider_names,
            index=provider_names.index(current_provider) if current_provider in provider_names else 0,
            format_func=lambda x: next(
                (p["name"] for p in providers if p["id"] == x), x
            ),
        )

        # Update provider if changed
        if selected_provider != st.session_state.rag_engine.llm_provider.name.split()[0].lower():
            try:
                st.session_state.rag_engine.set_llm_provider(selected_provider)
                st.success(f"Switched to {selected_provider}")
            except Exception as e:
                st.error(f"Error switching provider: {e}")

        # Show provider info
        current_llm = st.session_state.rag_engine.llm_provider
        if current_llm.is_local:
            st.info("🔒 Running locally (offline)")
        else:
            st.warning("☁️ Using cloud API (requires internet)")

        st.markdown("---")

        # Conversation management
        st.subheader("Conversations")

        # New conversation button
        if st.button("➕ New Conversation", use_container_width=True):
            conv = st.session_state.chat_history.create_conversation()
            st.session_state.current_conversation_id = conv.id
            st.session_state.messages = []
            st.rerun()

        # List existing conversations
        conversations = st.session_state.chat_history.list_conversations()

        for conv in conversations:
            col1, col2 = st.columns([4, 1])

            with col1:
                is_current = conv.id == st.session_state.current_conversation_id
                button_type = "primary" if is_current else "secondary"

                if st.button(
                    f"💬 {conv.title[:25]}..." if len(conv.title) > 25 else f"💬 {conv.title}",
                    key=f"conv_{conv.id}",
                    use_container_width=True,
                    type=button_type,
                ):
                    st.session_state.current_conversation_id = conv.id
                    # Load messages
                    messages = st.session_state.chat_history.get_messages(conv.id)
                    st.session_state.messages = [
                        {"role": m.role, "content": m.content, "sources": m.sources}
                        for m in messages
                    ]
                    st.rerun()

            with col2:
                if st.button("🗑️", key=f"del_{conv.id}"):
                    st.session_state.chat_history.delete_conversation(conv.id)
                    if st.session_state.current_conversation_id == conv.id:
                        st.session_state.current_conversation_id = None
                        st.session_state.messages = []
                    st.rerun()

        st.markdown("---")

        # Index stats
        st.subheader("Index Status")
        try:
            stats = st.session_state.rag_engine.get_stats()
            index_stats = stats["index"]

            if index_stats["exists"]:
                st.metric("Documents", index_stats["points_count"])
                st.caption(f"Status: {index_stats['status']}")
            else:
                st.warning("No index found. Run ingest.py first.")
        except Exception as e:
            st.error(f"Cannot connect to Qdrant: {e}")


def render_chat():
    """Render the main chat interface."""
    st.title("Chat with your data")

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            # Show sources for assistant messages
            if message["role"] == "assistant" and message.get("sources"):
                with st.expander("📚 Sources"):
                    for i, source in enumerate(message["sources"], 1):
                        st.markdown(f"**Source {i}** ({source['metadata'].get('source_type', 'unknown')})")
                        st.caption(source["content"])
                        st.markdown("---")

    # Chat input
    if prompt := st.chat_input("Ask a question about your data..."):
        # Ensure we have a conversation
        if st.session_state.current_conversation_id is None:
            conv = st.session_state.chat_history.create_conversation(
                title=prompt[:50] + "..." if len(prompt) > 50 else prompt
            )
            st.session_state.current_conversation_id = conv.id

        # Add user message to display
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    result = st.session_state.rag_engine.query(
                        question=prompt,
                        conversation_id=st.session_state.current_conversation_id,
                    )

                    st.markdown(result["answer"])

                    # Show sources
                    if result["sources"]:
                        with st.expander("📚 Sources"):
                            for i, source in enumerate(result["sources"], 1):
                                st.markdown(
                                    f"**Source {i}** ({source['metadata'].get('source_type', 'unknown')})"
                                )
                                st.caption(source["content"])
                                st.markdown("---")

                    # Add to session messages
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": result["answer"],
                        "sources": result["sources"],
                    })

                except Exception as e:
                    st.error(f"Error generating response: {e}")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"Error: {e}",
                        "sources": None,
                    })


def main():
    """Main application entry point."""
    init_session_state()
    render_sidebar()
    render_chat()


if __name__ == "__main__":
    main()
