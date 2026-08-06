"""Streamlit Web Application for Groww FAQ Chatbot (Mutual Fund Facts Assistant).
Features:
- Dual-view UI: 💬 FAQ Chatbot & 📊 Pilot & Observability Dashboard
- ➕ New Chat reset capability
- Sidebar with 5 covered Groww schemes and supported question categories
- Prompt chips for instant queries
- Zero-PII sanitization & intent guardrail classification
- Groq Llama 3.3 70B synthesis with citation anchoring & disclaimer
- Live audit log viewer and on-demand freshness synchronization
"""

import os
import time
import pandas as pd
import streamlit as st

# Load environment variables (supports local .env and Streamlit Cloud secrets)
from dotenv import load_dotenv
load_dotenv()

try:
    if "GROQ_API_KEY" in st.secrets:
        os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
except Exception:
    pass

# Core RAG & Observability Modules
from ingestion.pipeline import IngestionPipeline
from ingestion.freshness import FreshnessEngine
from retrieval.pipeline import RetrievalPipeline
from retrieval.sanitizer import sanitize_query
from guardrail.classifier import IntentClassifier
from guardrail.taxonomy import IntentCategory, TaxonomyManager
from generation.formatter import AnswerFormatter
from generation.pipeline import GenerationPipeline
from observability.audit_logger import AuditLogger
from observability.analytics import AnalyticsEngine

# Page configuration
st.set_page_config(
    page_title="Groww FAQ Chatbot & Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Dark & Electric Blue Groww Aesthetic
st.markdown("""
<style>
    /* Global Dark Theme */
    .stApp {
        background-color: #0b0f19;
        color: #f1f5f9;
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #111827;
        border-right: 1px solid #1f2937;
    }
    
    /* Headers & Text */
    h1, h2, h3, h4, h5, h6 {
        color: #f8fafc !important;
        font-weight: 700;
    }
    
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #60a5fa 0%, #3b82f6 50%, #2563eb 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    
    .sub-title {
        color: #94a3b8;
        font-size: 0.95rem;
        margin-bottom: 1.2rem;
    }
    
    /* KPI Metric Cards */
    .metric-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #60a5fa;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #94a3b8;
        margin-top: 4px;
    }
    
    /* Scheme Cards in Sidebar */
    .scheme-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 12px;
    }
    .scheme-title {
        font-weight: 600;
        color: #60a5fa;
        font-size: 0.9rem;
        margin-bottom: 4px;
    }
    .scheme-types {
        font-size: 0.78rem;
        color: #94a3b8;
        line-height: 1.4;
    }
    
    /* Disclaimer Card */
    .disclaimer-card {
        background: rgba(30, 41, 59, 0.7);
        border-left: 3px solid #3b82f6;
        padding: 10px 14px;
        border-radius: 6px;
        color: #94a3b8;
        font-size: 0.8rem;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)


# Initialize Pipelines (Cached for High Performance)
@st.cache_resource
def get_pipelines():
    ingestion = IngestionPipeline()
    retrieval = RetrievalPipeline()
    taxonomy = TaxonomyManager()
    guardrail = IntentClassifier(taxonomy_manager=taxonomy)
    formatter = AnswerFormatter(ingestion_pipeline=ingestion)
    generation = GenerationPipeline(formatter=formatter)
    logger = AuditLogger()
    analytics = AnalyticsEngine(
        audit_logger=logger,
        vector_store=retrieval.vector_store,
        ingestion_pipeline=ingestion
    )
    freshness = FreshnessEngine(
        ingestion_pipeline=ingestion,
        vector_store=retrieval.vector_store
    )
    return ingestion, retrieval, taxonomy, guardrail, formatter, generation, logger, analytics, freshness


(
    ingestion_pipeline,
    retrieval_pipeline,
    taxonomy_manager,
    guardrail_classifier,
    answer_formatter,
    generation_pipeline,
    audit_logger,
    analytics_engine,
    freshness_engine
) = get_pipelines()

sources = ingestion_pipeline.get_sources()

# Sidebar: Navigation & Controls
with st.sidebar:
    st.markdown("### 🧭 Navigation")
    app_mode = st.radio(
        "Select View:",
        ["💬 FAQ Chatbot", "📊 Observability & Dashboard"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    # New Chat Button
    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "👋 Hello! I am your **Groww FAQ Assistant**. Ask me any factual question about expense ratios, exit loads, benchmarks, minimum SIPs, or risk ratings for the 5 covered HDFC schemes.",
                "intent": "greeting",
                "is_refusal": False
            }
        ]
        st.rerun()

    st.markdown("---")
    st.markdown("### 📈 Covered Schemes")
    st.markdown("<div style='font-size:0.8rem; color:#94a3b8; margin-bottom:12px;'>Facts sourced strictly from official Groww scheme pages:</div>", unsafe_allow_html=True)
    
    for s in sources:
        with st.expander(f"🔹 {s.name}", expanded=False):
            st.markdown(f"**URL:** [{s.name}]({s.url})")
            st.markdown("""
            **Supported Questions:**
            - 📊 **Expense Ratio (TER)**
            - 🎯 **Benchmark Index**
            - ⚠️ **SEBI Riskometer**
            - 💰 **Minimum SIP & Lumpsum**
            - 🚪 **Exit Load & Lock-in**
            """)
            
    st.markdown("---")
    st.markdown("### 🛡️ Guardrails & Policy")
    st.markdown("""
    - ✅ **Facts-Only**: Verifiable scheme details only
    - ❌ **No Advice**: Won't recommend, predict, or compare
    - 🔒 **Zero-PII**: Phone, PAN, Aadhaar automatically redacted
    """)
    
    st.markdown(f"""
    <div class="disclaimer-card">
        ⚖️ <b>Disclaimer:</b> {taxonomy_manager.disclaimer}
    </div>
    """, unsafe_allow_html=True)


# ==========================================
# VIEW 1: FAQ CHATBOT
# ==========================================
if app_mode == "💬 FAQ Chatbot":
    st.markdown('<div class="main-title">Groww FAQ Chatbot</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Your facts-only, verified mutual fund assistant covering 5 official Groww scheme pages.</div>', unsafe_allow_html=True)

    # Quick Prompts / Suggestion Chips
    st.markdown("##### 💡 Suggested Questions:")
    col1, col2, col3, col4 = st.columns(4)

    suggested_query = None
    with col1:
        if st.button("📊 HDFC Mid Cap Expense Ratio?", use_container_width=True):
            suggested_query = "What is the expense ratio for HDFC Mid Cap Fund?"
    with col2:
        if st.button("🎯 HDFC Flexi Cap Benchmark?", use_container_width=True):
            suggested_query = "What benchmark does HDFC Flexi Cap Fund track?"
    with col3:
        if st.button("💰 HDFC Small Cap Min SIP?", use_container_width=True):
            suggested_query = "What is the minimum SIP for HDFC Small Cap Fund?"
    with col4:
        if st.button("⚠️ HDFC Balanced Advantage Risk?", use_container_width=True):
            suggested_query = "What is the riskometer classification for HDFC Balanced Advantage Fund?"

    # Session State for Conversation History
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "👋 Hello! I am your **Groww FAQ Assistant**. Ask me any factual question about expense ratios, exit loads, benchmarks, minimum SIPs, or risk ratings for the 5 covered HDFC schemes.",
                "intent": "greeting",
                "is_refusal": False
            }
        ]

    # Render Message History
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar="📈" if msg["role"] == "assistant" else "👤"):
            st.markdown(msg["content"])
            if msg.get("pii_detected"):
                st.caption("🔒 *Note: Sensitive personal information (PII) in your query was automatically redacted before processing.*")

    # Process User Input
    prompt = st.chat_input("Ask a factual question (e.g. What is the exit load for HDFC Small Cap?)...")
    if suggested_query:
        prompt = suggested_query

    if prompt:
        # Display user query
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        # Process via RAG Pipeline
        start_time = time.perf_counter()
        sanitized_query, pii_detected = sanitize_query(prompt.strip())
        category, refusal = guardrail_classifier.evaluate(sanitized_query)

        response_text = ""
        is_refusal = False
        citation_url = None

        with st.chat_message("assistant", avatar="📈"):
            with st.spinner("Searching scheme knowledge base..."):
                # Branch 1: Pre-retrieval Refusal
                if category in [
                    IntentCategory.ADVISORY,
                    IntentCategory.COMPARATIVE,
                    IntentCategory.PERFORMANCE_PREDICTION,
                    IntentCategory.OUT_OF_CORPUS
                ]:
                    is_refusal = True
                    response_text = refusal.message
                    if refusal.educational_url:
                        response_text += f"\n\n🔗 [Learn more about investing guidelines]({refusal.educational_url})"
                    st.markdown(response_text)
                    
                    latency_ms = (time.perf_counter() - start_time) * 1000.0
                    audit_logger.log_transaction(
                        query=sanitized_query,
                        pii_detected=pii_detected,
                        intent_category=category.value,
                        is_refusal=True,
                        retrieved_chunk_ids=[],
                        response_text=response_text,
                        citation_url=None,
                        educational_url=refusal.educational_url,
                        formatter_passed=True,
                        latency_ms=latency_ms
                    )

                # Branch 2: Mixed Intent
                elif category == IntentCategory.MIXED_INTENT:
                    retrieval_res = retrieval_pipeline.retrieve(sanitized_query)
                    gen_res = generation_pipeline.generate(
                        query=sanitized_query,
                        chunks=retrieval_res["chunks"],
                        detected_scheme=retrieval_res["detected_scheme"],
                        is_mixed_intent=True
                    )
                    response_text = gen_res.text
                    citation_url = gen_res.citation_url
                    st.markdown(response_text)

                    latency_ms = (time.perf_counter() - start_time) * 1000.0
                    audit_logger.log_transaction(
                        query=sanitized_query,
                        pii_detected=pii_detected,
                        intent_category=category.value,
                        is_refusal=False,
                        retrieved_chunk_ids=[c.chunk_id for c in retrieval_res["chunks"]],
                        response_text=response_text,
                        citation_url=citation_url,
                        educational_url=taxonomy_manager.educational_url,
                        formatter_passed=gen_res.is_compliant,
                        latency_ms=latency_ms
                    )

                # Branch 3: Factual in-corpus Query
                else:
                    retrieval_res = retrieval_pipeline.retrieve(sanitized_query)
                    if retrieval_res.get("clarification_needed") and retrieval_res.get("clarification_message"):
                        response_text = retrieval_res["clarification_message"]
                        st.markdown(response_text)
                    else:
                        gen_res = generation_pipeline.generate(
                            query=sanitized_query,
                            chunks=retrieval_res["chunks"],
                            detected_scheme=retrieval_res["detected_scheme"],
                            is_mixed_intent=False
                        )
                        response_text = gen_res.text
                        citation_url = gen_res.citation_url
                        st.markdown(response_text)

                    latency_ms = (time.perf_counter() - start_time) * 1000.0
                    audit_logger.log_transaction(
                        query=sanitized_query,
                        pii_detected=pii_detected,
                        intent_category=category.value,
                        is_refusal=False,
                        retrieved_chunk_ids=[c.chunk_id for c in retrieval_res.get("chunks", [])],
                        response_text=response_text,
                        citation_url=citation_url,
                        educational_url=None,
                        formatter_passed=True,
                        latency_ms=latency_ms
                    )

            if pii_detected:
                st.caption("🔒 *Note: Sensitive personal information (PII) was automatically masked.*")

        # Store assistant response in history
        st.session_state.messages.append({
            "role": "assistant",
            "content": response_text,
            "intent": category.value,
            "is_refusal": is_refusal,
            "pii_detected": pii_detected
        })


# ==========================================
# VIEW 2: OBSERVABILITY & DASHBOARD
# ==========================================
else:
    st.markdown('<div class="main-title">Pilot & Observability Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Real-time metrics, guardrail adherence, zero-PII audit trail, and corpus freshness tracking.</div>', unsafe_allow_html=True)

    summary = analytics_engine.compute_summary(recent_logs_limit=50)

    # Top KPI Metrics Cards
    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    with kpi1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{summary.total_queries}</div>
            <div class="metric-label">Total Queries</div>
        </div>
        """, unsafe_allow_html=True)
    with kpi2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{summary.sentence_compliance_pct}%</div>
            <div class="metric-label">Compliance Pass Rate</div>
        </div>
        """, unsafe_allow_html=True)
    with kpi3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{summary.citation_coverage_pct}%</div>
            <div class="metric-label">Citation Coverage</div>
        </div>
        """, unsafe_allow_html=True)
    with kpi4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{summary.latency.get('p50_ms', 0):.1f} ms</div>
            <div class="metric-label">Median Latency (P50)</div>
        </div>
        """, unsafe_allow_html=True)
    with kpi5:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{summary.pii_interceptions}</div>
            <div class="metric-label">PII Redactions</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Section 1: Intent & Refusal Analytics
    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown("### 📊 Intent & Refusal Breakdown")
        refusal_data = {
            "Intent Category": [
                "Factual (In Corpus)",
                "Advisory (Refusal)",
                "Comparative (Refusal)",
                "Prediction (Refusal)",
                "Out-of-Corpus (Refusal)",
                "Mixed Intent"
            ],
            "Count": [
                summary.factual_queries,
                summary.refusal_breakdown.get("advisory", 0),
                summary.refusal_breakdown.get("comparative", 0),
                summary.refusal_breakdown.get("performance_prediction", 0),
                summary.refusal_breakdown.get("out_of_corpus", 0),
                summary.refusal_breakdown.get("mixed_intent", 0)
            ]
        }
        st.dataframe(pd.DataFrame(refusal_data), use_container_width=True, hide_index=True)

    with col_right:
        st.markdown("### 🔄 Ingestion & Corpus Freshness")
        freshness_rows = []
        for status in summary.corpus_freshness:
            freshness_rows.append({
                "Scheme": status.scheme_name,
                "Chunks": status.chunk_count,
                "Last Ingested": status.fetched_at,
                "Last Verified": status.last_verified_unchanged_at,
                "Status": "🟢 Fresh" if status.is_fresh else "🟡 Stale"
            })
        st.dataframe(pd.DataFrame(freshness_rows), use_container_width=True, hide_index=True)

        if st.button("⚡ Run Freshness Sync Now", use_container_width=True):
            with st.spinner("Checking SHA-256 hashes across Groww scheme pages..."):
                freshness_res = freshness_engine.run_freshness_job()
                st.success(f"Freshness check completed! {freshness_res.unchanged_chunks} unchanged chunks verified in {freshness_res.duration_seconds}s.")
                st.rerun()

    st.markdown("---")

    # Section 2: Zero-PII Audit Logs
    st.markdown("### 📝 Live Zero-PII Audit Logs")
    if summary.recent_logs:
        log_rows = []
        for log in summary.recent_logs:
            log_rows.append({
                "Timestamp": log.timestamp[:19].replace("T", " "),
                "Sanitized Query": log.sanitized_query,
                "PII Stripped": "🛡️ Yes" if log.pii_detected else "No",
                "Intent Category": log.intent_category,
                "Refusal": "❌ Refusal" if log.is_refusal else "✅ Answered",
                "Latency": f"{log.latency_ms:.1f} ms" if log.latency_ms else "N/A",
                "Compliant": "✅ Passed" if log.formatter_passed else "❌ Failed"
            })
        st.dataframe(pd.DataFrame(log_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No audit logs captured yet. Ask questions in the FAQ Chatbot view to populate real-time logs!")
